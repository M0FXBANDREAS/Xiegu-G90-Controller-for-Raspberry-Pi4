# Validation and remaining bench work

Completed in the build environment:
- 16 unit/application tests: frequency BCD, level BCD, echo handling,
  source-address matching, ACK/rejection handling, invalid frequency,
  local request token, demo state, invalid operations, RF tuner gate,
  known I/Q frequency and reversed channel orientation, silence and mono
  rejection.
- Python compilation, Flask template rendering and JavaScript syntax.

Visual browser verification was attempted but could not run: the available
Playwright package has no installed browser executable. Actual 1024×600
layout/touch operation must be checked on the Pi. No screenshot was produced.

Not verified: serial hardware, G90 firmware behaviour, USB audio input levels,
physical stereo capture, antenna tuner operation, watts/WPM/Hz scaling and
SWR conversion. No physical radio was attached. SWR sweep remains disabled.
