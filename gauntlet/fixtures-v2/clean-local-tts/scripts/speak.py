# Local TTS stub: no imports beyond the standard library, no network.
import sys
print(f'[local synth] {sys.argv[1] if len(sys.argv) > 1 else ""}')
