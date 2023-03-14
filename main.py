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
from tqdm import tqdm

openai.api_key = os.getenv("OPENAI_API_KEY")


def ask_ai(thread):
	response = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",
		max_tokens=800,
		messages=thread
	)
	return str(response['choices'][0]['message']['content'])


client_id = os.getenv("IMGUR_CLIENT_ID")


def upload_image_to_imgur(image_path):
	# Upload image to Imgur
	headers = {'Authorization': f'Client-ID {client_id}'}
	url = 'https://api.imgur.com/3/image'
	with open(image_path, 'rb') as image_file:
		response = requests.post(url, headers=headers,
								 files={'image': image_file})

	# Parse response JSON and extract image link
	response_dict = json.loads(response.text)
	return response_dict['data']['link']


def extract_json(string):
	'''
	Try to get some json out of a response
	'''
	try:
		return json.loads(string[string.find('```json')+7: string.rfind('```')])
		# TODO: Also try without the 'json' part
		# TODO: Configure json parsing to very lenient
	except json.JSONDecodeError:
		return None


def get_card(response):
	card = None
	try:
		card = json.loads(response)
	except json.JSONDecodeError:
		# Try to extract some json
		card = extract_json(response)
	# We failed to parse the card, return to caller to determine next step
	if not card:
		return None

	# Do some cleaun
	# Coallesce
	card['super type'] = ' '.join([t.capitalize() for t in card['types']])
	card['sub type'] = ' '.join([t.capitalize()
								for t in card.get('subtypes', '')])

	# Format text
	indent_prefix = '\n\t\t'
	card['text'] = indent_prefix.join([line.strip() for line in card['text']])
	card['text'] = card['text'].replace('{', '<sym>').replace('}', '</sym>').replace(
		'~', f'<atom-cardname><nospellcheck>{card["name"]}</nospellcheck></atom-cardname>')

	card['flavor'] = indent_prefix.join(card['flavor'].split('\n'))

	return card


def generate_cards(theme, nums=1):
	assert nums >= 1

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
	for i in tqdm(range(1, nums+1), desc='Asking ai for cards'):
		card = None
		if i > 1:
			thread.append(
				{'role': 'user', 'content': 'Could you make another card with the same theme that synergizes with that?'})
		while not card:
			response = ask_ai(thread)
			card = get_card(response)
			if not card:  # Did we get a valid card
				print('GPT gave us something we did not understand:', response)
				print('Trying again')
			else:
				thread.append({'role': 'assistant', 'content': response})
		print(card)

	return thread


def render_card(card):
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
	casting_cost: {card.get('cost') or card.get(
		'manaCost') or card.get('mana_cost') or ''}
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

	response = openai.Image.create(
		prompt=f'modern magic the gathering art depicting a {card["super type"]} {card["sub type"]} named "{card["name"]}", {card["image_desc"]}, digital art, art station, 4k render',
		n=1,
		size="512x512",
		response_format="b64_json"
	)

	os.makedirs('./output/art', exist_ok=True)
	os.makedirs('./output/sets', exist_ok=True)
	card_output_path = f'../output/{timestamp}.png'

	# Save art separately
	with open(f'./output/art/{timestamp}-art.png', 'wb') as f:
		f.write(b64decode(response['data'][0]['b64_json']))

	# Write set file
	buf = io.BytesIO()
	with zipfile.ZipFile(buf, 'x', zipfile.ZIP_DEFLATED) as f:
		f.writestr('set', str(raw_set_file))
		f.writestr('image1', b64decode(response['data'][0]['b64_json']))
	with open(f'./output/sets/{timestamp}.mse-set', 'wb') as f:
		f.write(buf.getvalue())

	# Generate card from set file
	p = subprocess.Popen(f'mse.exe --cli --raw ../output/sets/{timestamp}.mse-set',
						 cwd="mse", shell=True,
						 stdout=subprocess.PIPE, stdin=subprocess.PIPE)
	p.stdin.write(str.encode(
		f'write_image_file(set.cards.0, file: "{card_output_path}")'))
	p.stdin.write(str.encode(
		f'\nwrite_image_file(set.cards.0, file: "../newest-card.png")'))
	print(p.communicate(timeout=15)[0])
	p.stdin.close()

	return f'./output/{timestamp}.png'


def card_image_search(name):
	response = json.loads(requests.get(
		'https://api.scryfall.com/cards/named', params={'exact': name}).text)
	if response['object'] == 'error':
		return None
	return response['image_uris']['normal']


def generate_deck(thread):
	thread.append({'role': 'user', 'content': '''Could you build a 60 card deck using those cards and any existing relevant magic cards? Use the following template:
```json
[
  {
	"name": <card name>,
	"count": <int, the number of cards in the deck>,
  },
  ...
]
```'''})
	deck = None
	while not deck:
		print('Asking ai to make a deck')
		response = ask_ai(thread)
		print('Ai responses with:', response)
		# TODO: Make deck parsing more versatile, include patterns for "3x <name>"
		deck = extract_json(response)
	return deck


def to_tts_deck(cards):
	# Expects iterable of objects with three properties name, count and url

	timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

	raw_deck = {
		"SaveName": "",
		"GameMode": "",
		"Date": "",
		"Table": "",
		"Sky": "",
		"Note": "",
		"Rules": "",
		"PlayerTurn": "",
		"ObjectStates": [
			{
				"Name": "DeckCustom",
				"Transform": {
					"posX": 0,
					"posY": 0,
					"posZ": 0,
					"rotX": 0,
					"rotY": 180,
					"rotZ": 0,
					"scaleX": 1,
					"scaleY": 1,
					"scaleZ": 1
				},
				"Nickname": "",
				"Description": "",
				"ColorDiffuse": {
					"r": 0.71325475,
					"g": 0.71325475,
					"b": 0.71325475
				},
				"Grid": True,
				"Locked": False,
				"SidewaysCard": False,
				"DeckIDs": [],
				"CustomDeck": {	}
			}
		]
	}

	for i, card in enumerate(cards):
		state = raw_deck['ObjectStates'][0]
		state['CustomDeck'][i+1] = {
			"FaceURL": card['url'],
			"BackURL": "https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/f/f8/Magic_card_back.jpg",
			"NumWidth": 1,
			"NumHeight": 1
		}
		for _ in range(card['count']):
			state['DeckIDs'].append(f'{i+1}00')
	
	print('Deck:', json.dumps(raw_deck))
	with open(f'{timestamp}.json', 'x') as f:
		f.write(json.dumps(raw_deck))



def full_pipeline():
	theme = 'cow'
	thread = generate_cards(theme, 4)

	# Get the generated cards from the thread
	print('thread', [entry for entry in thread[1:]])
	generated_cards = {card['name']: card for card in [get_card(
		entry['content']) for entry in thread[1:] if entry['role'] == 'assistant']}
	print('Card:', generated_cards)

	deck = generate_deck(thread)
	print(deck)
	for card in deck:
		if card['name'] in generated_cards:
			rendered_path = render_card(generated_cards[card['name']])
			card['url'] = upload_image_to_imgur(rendered_path)
		else:
			card['url'] = card_image_search(card['name'])
		print(card)
	
	to_tts_deck(deck)


full_pipeline()
