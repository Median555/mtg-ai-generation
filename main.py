import sys
import os
import zipfile
import io
import subprocess
from textwrap import indent
import openai
import json
import datetime
from base64 import b64decode

openai.api_key = os.getenv("OPENAI_API_KEY")

theme = 'cow tribal'

prompt = f'''Could you generate a new magic card? It should have a theme around "{theme}". Output it as json and use this template:
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

# Could you make another card with the same theme that synergizes with that?
# Could you build deck using those cards and any existing relevant magic cards?

card = None

while not card:
	response = openai.ChatCompletion.create(
	model="gpt-3.5-turbo",
	max_tokens=400,
	messages=[
			{"role": "user", "content": prompt},
		]
	)
	response = str(response['choices'][0]['message']['content'])
	try:
		card = json.loads(response)
		break
	except json.JSONDecodeError:
		# Try to extract some json
		possible_json = response[response.find('```json')+7 : response.rfind('```')]
		try:
			card = json.loads(possible_json)
			break
		except json.JSONDecodeError:
			print('GPT gave us something we did not understand:', response)
			print('Trying again')
	
	# TODO: Ask GPT to correct cards if not quite right, like:
	#  non-creatures having power and toughness
	#  creatures having no power and toughness
	#  enchantments having sorcery/instant like abilities (how to check this?)

print(card)

# Coallesce
card['super type'] = ' '.join([t.capitalize() for t in card['types']])
card['sub type'] = ' '.join([t.capitalize() for t in card.get('subtypes', '')])

# Format text
indent_prefix = '\n\t\t'
card['text'] = indent_prefix.join([line.strip() for line in card['text']])
card['text'] = card['text'].replace('{', '<sym>').replace('}', '</sym>').replace('~', f'<atom-cardname><nospellcheck>{card["name"]}</nospellcheck></atom-cardname>')
#
card['flavor'] = indent_prefix.join(card['flavor'].split('\n'))


raw_set_file = f'''
mse_version: 2.0.2
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

#print(raw_set_file)
timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

response = openai.Image.create(
	prompt=f'modern magic the gathering card art depicting a {card["super type"]} {card["sub type"]} named "{card["name"]}", {card["image_desc"]}, digital art, art station, 4k render',
	n=1,
	size="512x512",
	response_format="b64_json"
)

# Save art separately
with open(f'./output/{timestamp}-art.png', 'wb') as f:
	f.write(b64decode(response['data'][0]['b64_json']))

# Write set file
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'x', zipfile.ZIP_DEFLATED) as f:
	f.writestr('set', str(raw_set_file))
	f.writestr('image1', b64decode(response['data'][0]['b64_json']))
with open(f'./output/{timestamp}.mse-set', 'wb') as f:
	f.write(buf.getvalue())

# Generate card from set file
p = subprocess.Popen(f'mse.exe --cli --raw ../output/{timestamp}.mse-set',
	cwd="mse", shell=True,
	stdout=subprocess.PIPE, stdin=subprocess.PIPE)
p.stdin.write(str.encode(f'write_image_file(set.cards.0, file: "../output/{card["name"]}.png")'))
p.stdin.write(str.encode(f'\nwrite_image_file(set.cards.0, file: "../newest-card.png")'))
print(p.communicate(timeout=15)[0])
p.stdin.close()



# Clean up
#os.remove('set.mse-set')