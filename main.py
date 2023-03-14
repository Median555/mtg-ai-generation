import os
import zipfile
import io
import subprocess
from textwrap import indent
import openai
import json
import datetime
from base64 import b64decode
import requests

openai.api_key = os.getenv("OPENAI_API_KEY")


def get_card(response):
	card = None
	try:
		card = json.loads(response)
	except json.JSONDecodeError:
		# Try to extract some json
		possible_json = response[response.find('{') : response.rfind('}')+1]
		try:
			card = json.loads(possible_json)
		except json.JSONDecodeError:
			pass
	# We failed to parse the card, return to caller to determine next step
	if not card:
		return None
	
	# Do some cleaun
	# Coallesce
	card['super type'] = ' '.join([t.capitalize() for t in card['types']])
	card['sub type'] = ' '.join([t.capitalize() for t in card.get('subtypes', '')])

	# Format text
	indent_prefix = '\n\t\t'
	card['text'] = indent_prefix.join([line.strip() for line in card['text']])
	card['text'] = card['text'].replace('{', '<sym>').replace('}', '</sym>').replace('~', f'<atom-cardname><nospellcheck>{card["name"]}</nospellcheck></atom-cardname>')
	
	card['flavor'] = indent_prefix.join(card['flavor'].split('\n'))

	return card


def generate_cards(theme, nums=1):
	assert nums >= 1

	out = list()

	start_prompt = f'''Could you generate a new magic card? It should have a theme around "{theme}". Output it as json and use this template:
```json
{{
	"name": <name>,
	"text": <formatted text, lines in array>,
	"cost": <mana cost>,
	"rarity": <common, uncommon, rare or mythic rare>,
	"types:" <super types array>,
	"subtypes": <sub types array>,
	"power": <power>,
	"toughness": <toughness>,
	"flavor": <flavor text>,
	"image_desc": <image description> 
}}
```'''

	thread = [{"role": "user", "content": start_prompt}]

	# Could you build deck using those cards and any existing relevant magic cards?

	# TODO: Ask GPT to correct cards if not quite right, like:
	#  non-creatures having power and toughness
	#  creatures having no power and toughness
	#  enchantments having sorcery/instant like abilities (how to check this?)
	for i in range(1, nums+1):
		card = None
		while not card:
			response = openai.ChatCompletion.create(
				model="gpt-3.5-turbo",
				max_tokens=400,
				messages=thread
			)
			response = str(response['choices'][0]['message']['content'])
			card = get_card(response)
			if not card: # Did we get a valid card
				print('GPT gave us something we did not understand:', response)
				print('Trying again')
			else:
				out.append(card)
				thread.append({'role': 'assistant', 'content': response})
				thread.append({'role': 'user', 'content': 'Could you make another card with the same theme that synergizes with that?'})
				print(thread)
	
	return out

def render_card(card, backend):
	raw_set_file = f'''mse_version: 2.0.2
game: magic
game_version: 2020-04-25
stylesheet: m15-altered
stylesheet_version: 2023-02-13
set_info:
	symbol: 
	masterpiece_symbol: 
styling:
	magic-m15-altered:
		text_box_mana_symbols: magic-mana-small.mse-symbol-font
		level_mana_symbols: magic-mana-large.mse-symbol-font
		overlay: 
card:
	has_styling: false
	notes: 
	name: {card.get('name') or card.get('title')}
	casting_cost: {card.get('cost') or card.get('manaCost') or card.get('mana_cost') or ''}
	image: image1
	super_type: <word-list-type>{card['super type']}</word-list-type>
	sub_type: {card['sub type']}
	rule_text: 
		{card.get('text')}
	flavor_text:
		<i-flavor>{card['flavor']}</i-flavor>
	power: {card.get('power') or ''}
	toughness: {card.get('toughness') or ''}
	card_code_text: "AI"
	rarity: {(card.get('rarity') or '').lower()}
	image_2: 
	mainframe_image: 
	mainframe_image_2: 
version_control:
	type: none
apprentice_code: 
'''

	timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

	image_data = None
	image_prompt = f'modern magic the gathering art depicting a {card["super type"]} {card["sub type"]} named "{card["name"]}", {card["image_desc"]}, digital art, art station, 4k render'

	if(backend == 'dalle'):
		response = openai.Image.create(
			prompt=image_prompt,
			n=1,
			size="512x512",
			response_format="b64_json"
		)

		image_data = response['data'][0]['b64_json']
	
	elif(backend == 'stablediffusion'):
		api_url = 'http://127.0.0.1:7860/sdapi/v1/txt2img'
		payload = {'prompt': image_prompt, 'width': 512, 'height':512, 'steps': 50}
		response = requests.post(url=api_url, json=payload).json()

		image_data = response['images'][0]

	assert image_data is not None


	os.makedirs('./output/art', exist_ok=True)
	os.makedirs('./output/sets', exist_ok=True)
	card_output_path = f'../output/{timestamp}.png'

	# Save art separately
	with open(f'./output/art/{timestamp}-art.png', 'wb') as f:
		f.write(b64decode(image_data))

	# Write set file
	buf = io.BytesIO()
	with zipfile.ZipFile(buf, 'x', zipfile.ZIP_DEFLATED) as f:
		f.writestr('set', str(raw_set_file))
		f.writestr('image1', b64decode(image_data))
	with open(f'./output/sets/{timestamp}.mse-set', 'wb') as f:
		f.write(buf.getvalue())

	# Generate card from set file
	p = subprocess.Popen(f'mse.exe --cli --raw ../output/sets/{timestamp}.mse-set',
		cwd="mse", shell=True,
		stdout=subprocess.PIPE, stdin=subprocess.PIPE)
	p.stdin.write(str.encode(f'write_image_file(set.cards.0, file: "{card_output_path}")'))
	p.stdin.write(str.encode(f'\nwrite_image_file(set.cards.0, file: "../newest-card.png")'))
	print(p.communicate(timeout=15)[0])
	p.stdin.close()

	return card_output_path

theme ='cow tribal'
cards = generate_cards(theme, 2)
for card in cards:
	print(render_card(card, 'dalle'), card)