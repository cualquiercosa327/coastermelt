# Functions for poking at the MT1939's miscellaneous memory-mapped hardware
# and memory-mapped memory-mapping hardware.

__all__ = [
    'poke_orr', 'poke_bic',
    'ivt_find_target', 'ivt_set', 'ivt_get',
    'overlay_set', 'overlay_get', 'reset_arm',
]

import code


def poke_orr(d, address, word):
    """Read-modify-write sequence to bitwise OR, named after the ARM instruction"""
    d.poke(address, d.peek(address) | word)


def poke_bic(d, address, word):
    """Read-modify-write to bitwise AND with the inverse, named after the ARM instruction"""
    d.poke(address, d.peek(address) & ~word)


def ivt_find_target(d, address):
    """Disassemble an instruction in the IVT to locate the jump target"""
    text = code.disassemble(d, address, 4, thumb=False)
    return code.ldrpc_source_address(code.disassembly_lines(text)[0])


def ivt_get(d, address):
    """Read the target address of a long jump in the interrupt vector table"""
    return d.peek(ivt_find_target(d, address))


def ivt_set(d, address, handler):
    """Change the target address of a jump in the interrupt vector table.
    Assumes the table is in RAM.
    """
    d.poke(ivt_find_target(d, address), handler)


def overlay_set(d, address, wordcount = 1):
    """Set up a RAM overlay region, up to 4kB, mappable anywhere in the low 8MB.
    If address is None, disables the overlay.
    """
    control = 0x4011f04
    poke_bic(d, control, 0x200)
    poke_bic(d, control, 0x2000)
    if address is None:
        d.poke(control + 0x0c, 0xffffffff)
        d.poke(control + 0x10, 0x00000000)
    else:
        if address & 3:
            raise ValueError("Overlay mapping address must be word aligned")
        d.poke(control + 0x0c, address)
        d.poke(control + 0x10, address + wordcount*4 - 1)
        poke_orr(d, control, 0x200)
        poke_orr(d, control, 0x2000)


def overlay_get(d):
    """Get the current extent of the RAM overlay.
    Returns an (address, wordcount) tuple.
    """
    control = 0x4011f04
    address = d.peek(control + 0x0c)
    limit = d.peek(control + 0x10)
    return (address, (limit - address + 3) / 4)


def reset_arm(d):
    """Provoke a system reset by calling the reset vector"""
    try:
        d.blx(0)
    except IOError:
        # Expect that SCSI command to fail. Reconnect.
        d.reset()
