# TODO / Roadmap

## Two engines, one mentor (planned)

This project (`Brainia`) is the `Brain/` of an `AI-Coached-Life` container (see README "Where this fits"). It is **engine-agnostic**: a second brain configured as a life-coach mentor, independent of which underlying framework powers it. The engine brand lives inside `Brain/`; the container does not carry it.

There are two engine forks:

- **COG** — current engine. Everything in this repo today runs on the COG fork ([huytieu/COG-second-brain](https://github.com/huytieu/COG-second-brain), tracked as the `upstream` remote). Complete and working now.
- **gbrain / "second brain"** — future personalized engine. Not built yet. **TO-DO.**

Today the entire mentor lives on the COG fork. The gbrain-based variant is planned and will be added later. Keep the framing engine-agnostic so the switch (or coexistence) is clean when gbrain is ready.
