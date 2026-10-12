#include <stdint.h>

/* Inferred name for the Ultra Sun base startup routine at 0x00100024.
 * Bounds are the logical end of .data and the end of BSS in this target.
 * Volatile stores preserve the observed word-by-word clearing behavior.
 */
void ultrasun_clear_bss(void)
{
    for (uintptr_t address = UINT32_C(0x006a3d48);
         address < UINT32_C(0x006d3f04); address += sizeof(uint32_t)) {
        *(volatile uint32_t *)address = 0;
    }
}
