// Phase stepping coil transfers by DMA SPI on the AT32F403A
//
// The generic poll backend sends each coil write with a blocking
// spi_transfer() from the scheduler timer, which runs with irqs disabled.
// Five bytes at the TMC SPI rate take ~10us, longer than one byte time on
// the 921600 baud host link, so the USART lost bytes while phase stepping.
// Here the update only starts DMA transfers, one per bus, and the next
// tick releases the chip selects once they have finished.
//
// The AT32F403A DMA channels are register compatible with the stm32f1.
// SPI4 has no fixed stm32f1 request line, so the controller's flexible
// request mapping is used for every bus.
//
// Adapted from stm32/phase_stepper_dma.c in Hannott/kalico, which is
// Copyright (C) 2026  Åsmund Collin <aakjaergaard@gmail.com>
//
// This file may be distributed under the terms of the GNU GPLv3 license.

#include "command.h" // shutdown
#include "compiler.h" // ARRAY_SIZE
#include "gpio.h" // struct spi_config
#include "internal.h" // DMA1
#include "phase_stepper.h" // phase_board_xfer_start
#include "sched.h" // sched_shutdown

// AT32 DMA flexible request registers (not in the stm32f1 headers)
#define DMA_SRC_SEL0(dma) (*(volatile uint32_t *)((uint32_t)(dma) + 0xa0))
#define DMA_SRC_SEL1(dma) (*(volatile uint32_t *)((uint32_t)(dma) + 0xa4))
#define DMA_FLEX_EN (1 << 24)

#ifndef SPI4
#define SPI4 ((SPI_TypeDef *)(APB1PERIPH_BASE + 0x00004000UL))
#endif

struct dma_map {
    SPI_TypeDef *spi;
    DMA_Channel_TypeDef *chan;
    uint8_t chan_num, request;
};

// One DMA1 channel per bus, so steppers on different buses each keep
// their channel configured. No other firmware code uses DMA1.
static const struct dma_map dma_maps[] = {
    { SPI1, DMA1_Channel3, 3, 0x0a }, // spi1_tx
    { SPI2, DMA1_Channel5, 5, 0x0c }, // spi2_tx
#ifdef SPI3
    { SPI3, DMA1_Channel2, 2, 0x0e }, // spi3_tx
#endif
    { SPI4, DMA1_Channel4, 4, 0x10 }, // spi4_tx
};

static const struct dma_map *
lookup_map(SPI_TypeDef *spi)
{
    uint32_t i;
    for (i = 0; i < ARRAY_SIZE(dma_maps); i++)
        if (dma_maps[i].spi == spi)
            return &dma_maps[i];
    return NULL;
}

static void
set_request(const struct dma_map *m)
{
    uint32_t shift = ((m->chan_num - 1) & 3) * 8;
    if (m->chan_num <= 4)
        DMA_SRC_SEL0(DMA1) = ((DMA_SRC_SEL0(DMA1) & ~(0xff << shift))
                              | (m->request << shift));
    else
        DMA_SRC_SEL1(DMA1) = ((DMA_SRC_SEL1(DMA1) & ~(0xff << shift))
                              | (m->request << shift) | DMA_FLEX_EN);
}

static uint32_t
request_of(const struct dma_map *m)
{
    uint32_t shift = ((m->chan_num - 1) & 3) * 8;
    uint32_t reg = m->chan_num <= 4 ? DMA_SRC_SEL0(DMA1) : DMA_SRC_SEL1(DMA1);
    return (reg >> shift) & 0xff;
}

static void
clear_flags(const struct dma_map *m)
{
    DMA1->IFCR = 0xf << ((m->chan_num - 1) * 4);
}

void
phase_board_xfer_setup(struct spi_config *config)
{
    const struct dma_map *m = lookup_map(config->spi);
    if (!m)
        shutdown("Phase stepping not supported on this SPI bus");
    RCC->AHBENR |= RCC_AHBENR_DMA1EN;
    RCC->AHBENR;
    // Flexible mapping applies to every DMA1 channel once enabled
    DMA_SRC_SEL1(DMA1) |= DMA_FLEX_EN;
    set_request(m);
    DMA_Channel_TypeDef *chan = m->chan;
    chan->CCR = 0;
    chan->CPAR = (uint32_t)&m->spi->DR;
    // Memory to peripheral, byte wide, memory increment, high priority
    uint32_t ccr = DMA_CCR_DIR | DMA_CCR_MINC | DMA_CCR_PL_1;
    chan->CCR = ccr;
    if (chan->CCR != ccr || chan->CPAR != (uint32_t)&m->spi->DR
        || !(DMA_SRC_SEL1(DMA1) & DMA_FLEX_EN) || request_of(m) != m->request)
        shutdown("Phase stepper DMA not responding");
    clear_flags(m);
}

void
phase_board_xfer_start(struct spi_config *config, uint8_t *data
                       , uint_fast8_t len)
{
    const struct dma_map *m = lookup_map(config->spi);
    DMA_Channel_TypeDef *chan = m->chan;
    chan->CCR &= ~DMA_CCR_EN;
    clear_flags(m);
    chan->CMAR = (uint32_t)data;
    chan->CNDTR = len;
    chan->CCR |= DMA_CCR_EN;
    // TXE is set, so enabling the request starts the transfer
    m->spi->CR2 |= SPI_CR2_TXDMAEN;
}

int
phase_board_xfer_done(struct spi_config *config)
{
    const struct dma_map *m = lookup_map(config->spi);
    if (m->chan->CNDTR)
        return 0;
    // The last byte leaves the shift register after the DMA count is zero
    return (m->spi->SR & (SPI_SR_TXE | SPI_SR_BSY)) == SPI_SR_TXE;
}

void
phase_board_xfer_finish(struct spi_config *config)
{
    const struct dma_map *m = lookup_map(config->spi);
    m->spi->CR2 &= ~SPI_CR2_TXDMAEN;
    m->chan->CCR &= ~DMA_CCR_EN;
    clear_flags(m);
    // The transfer was transmit only: drop the received byte and clear
    // the resulting overrun so the next polled transfer starts clean.
    while (m->spi->SR & SPI_SR_RXNE)
        (void)m->spi->DR;
    (void)m->spi->SR;
}

void
phase_board_xfer_abort(struct spi_config *config)
{
    const struct dma_map *m = lookup_map(config->spi);
    m->chan->CCR &= ~DMA_CCR_EN;
    // Let any byte already in the shift register finish before release
    uint32_t i;
    for (i = 0; i < 1000 && (m->spi->SR & SPI_SR_BSY); i++)
        ;
    phase_board_xfer_finish(config);
}

// Each bus has its own DMA channel, so transfers on different buses run
// at the same time.
uint32_t
phase_board_xfer_bus(struct spi_config *config)
{
    return (uint32_t)config->spi;
}
