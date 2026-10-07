# G90 CI-V command map

Frame: `FE FE <radio address> E0 <command> <data> FD`.
Default radio address 88 hex; configurable 70 fallback.
19200 baud, 8N1, no hardware flow control.
Frequency uses five packed BCD bytes, least significant pair first.
Levels use two packed BCD bytes, most significant pair first, 0000–0255.
Radio replies use destination E0 and source radio address. FB is ACK; FA
is rejection. Cable echoes must not be mistaken for a radio reply.

| Function | Command bytes (hex) | Data |
|---|---|---|
| Alternate frequency setter | 00 | 5-byte BCD frequency |
| Alternate mode setter | 01 | mode |
| Frequency edges | 02 | query |
| Frequency read/set | 03 / 05 | query / 5-byte BCD |
| Mode read/set | 04 / 06 | query / mode, optional filter byte |
| VFO mode / A / B / swap | 07 / 07 00 / 07 01 / 07 B0 | no payload |
| Split | 0F | 00 off / 01 on |
| ATT | 11 | query / documented toggle setter |
| AF | 14 01 | query / BCD level |
| SQL | 14 03 | query / BCD level |
| CW sidetone | 14 09 | query / BCD level |
| RF power | 14 0A | query / BCD level |
| CW speed | 14 0C | query / BCD level |
| Squelch status | 15 01 | query |
| S-meter | 15 02 | query |
| RF power meter | 15 11 | query |
| SWR meter | 15 12 | query |
| PRE | 16 02 | query / 00 off / 01 on |
| AGC | 16 12 | query / 00–03 (verify labels on firmware) |
| NB | 16 22 | query / 00 off / 01 on |
| COMP | 16 44 | query / 00 off / 01 on |
| Dial lock | 16 50 | query / 00 unlocked / 01 locked |
| PTT | 1C 00 | query / 00 receive / 01 transmit |
| ATU | 1C 01 | query / 00 bypass / 01 enabled / 02 tune |

Mode bytes: LSB 00, USB 01, AM 02, CW 03, NFM 05 (firmware dependent),
CWR 07. Newer DATA modes/extensions need separate verification.
Additional model probes in Hamlib include 19 00 and 1D 19. Selected VFO
commands 25/26 have firmware quirks and are not used here.

Example: set 14.200 MHz using address 88:
`FE FE 88 E0 05 00 00 20 14 00 FD`.

This file is a published baseline, not proof every command works with every
firmware. No verified built-in SWR scanner start/download command exists in
the consulted tables. A newer manual describes `1A 05 00 10` filter settings;
this project leaves them disabled pending firmware-specific verification.
