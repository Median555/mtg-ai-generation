# What's this?

A Frankensteins monster of a script, gluing different APIs and programs together. It's purpose? To generate completely new Magic: The Gathering cards from user prompts and make playable decks out of these. Does it work? Kinda. Is it fun? Definitely!

The script uses OpenAI GPT Chat api to generate cards and Dalle or Stable Diffusion for "art". These a given to Magic Set Editor which renders them into bona fide magic cards. With another prompt to the Chat api, a deck is build which output a "playable" deck in Tabletop Simulators Save format.

Example outputs:

|Theme prompt|Generated cards|
| - | - |
| Cheese | ![](Curdling%20Conjurer.png) ![](Cheese%20Monger.png) |
| cow | ![](Moo-tant%20Herdmaster.png) ![](20230312150803.png) |
| Shrek | ![](20230308211944.png) |




# Setup

1. Download Magic Set Editor (Lite is fine) and put it in a folder named "mse" https://magicseteditor.boards.net/page/downloads
2. Add your OpenAI API key as an environment variable named "OPENAI_API_KEY" - [guide](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety). Make sure the enviroment variable is available by restarting any open terminal sessions (including VS Code)
3. Install `openai` python package - [pip](https://pypi.org/project/openai/) - [conda](https://anaconda.org/conda-forge/openai)
3. Run `main.py`

## Stable diffusion backend

It's possible to use stable diffusion instead of Dalle for art generation.

### Setup

1. Install a stable diffusion webUI - I used [AUTOMATIC1111's project](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
2. Add `--api` to the `COMMANDLINE_ARGS` line in `webui-user.bat` so it reads `set COMMANDLINE_ARGS=--api`
3. Start the webui using the startup script
4. Change the `render_card` backend parameter to `stablediffusion`

# Notes

1. Enchantments sometimes have effects with no trigger. 

# TODO

1. Better checking of missing fields
2. Deck generation
3. Fetching of real cards
4. Tabletop Simulator deck generation


# LICENSE

Output from this program is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

Copyright 2023 Mikkel Pilegaard

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.