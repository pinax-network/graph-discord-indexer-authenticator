import asyncio
import logging
import os
import secrets
import threading

import discord
import requests

from discord.ext import commands
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from flask import Flask, jsonify, request
from flask_cors import CORS
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load env
load_dotenv()

# Discord bot configuration
ADDR = os.getenv('ADDR')
PORT = os.getenv('PORT')
TOKEN = os.getenv('TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
ROLE_ID = os.getenv('ROLE_ID')
FRONTEND_URL = os.getenv('FRONTEND_URL')

SIGNING_MESSAGE = 'Please sign this message to verify your wallet address: {}'

# GraphQL configuration
GRAPHQL_URL = 'https://api.thegraph.com/subgraphs/name/graphprotocol/graph-network-arbitrum'
WHITELIST_QUERY = gql('''
{
  indexers(first: 1000) {
    account {
      id
      operators {
        id
      }
    }
  }
}
''')

# Flask app configuration
app = Flask(__name__)
CORS(app)

# Discord bot intents and initialization
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Store pending verifications
pending_verifications = {}

# Store whitelisted addresses
whitelisted_addresses = set()

# Fetch the whitelist
def fetch_whitelist():
    try:
        transport = RequestsHTTPTransport(
            url=GRAPHQL_URL,
            verify=True,
            retries=3,
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)
        result = client.execute(WHITELIST_QUERY)
        logging.debug(f'Whitelist result: {result}')
        
        for indexer in result['indexers']:
            whitelisted_addresses.add(indexer['account']['id'].lower())
            for operator in indexer['account']['operators']:
                whitelisted_addresses.add(operator['id'].lower())
        
        logging.info(f'Fetched {len(whitelisted_addresses)} whitelisted addresses')
    except Exception as e:
        logging.error(f'Error fetching whitelist: {e}')

@app.route('/verify', methods=['POST'])
def verify():
    try:
        data = request.json
        logging.debug(f'Received data: {data}')
        
        token = data.get('token')
        wallet_address = data.get('wallet_address')
        signature = data.get('signature')
        
        logging.debug(f'Token: {token}')
        logging.debug(f'Wallet Address: {wallet_address}')
        logging.debug(f'Signature: {signature}')

        if not token or not wallet_address or not signature:
            logging.error('Missing data: One or more fields are empty.')
            return jsonify({'error': 'Missing data'}), 400

        # Directly call the check_verification logic in the bot
        asyncio.run_coroutine_threadsafe(check_verification_logic(token, wallet_address, signature), bot.loop)

        return jsonify({'message': 'Verification successful'}), 200
    except Exception as e:
        logging.error(f'Error processing request: {e}')
        return jsonify({'error': 'Internal server error'}), 500

async def check_verification_logic(token: str, wallet_address: str, signature: str):
    try:
        if token not in pending_verifications:
            logging.debug(f'Invalid token: {token}')
            return

        user_id = pending_verifications.pop(token)
        user = await bot.fetch_user(user_id)
        guild = bot.get_guild(int(GUILD_ID))

        if not guild:
            logging.error(f'Guild not found: {GUILD_ID}')
            return

        member = guild.get_member(user_id)
        if not member:
            logging.error(f'Member not found in the guild: {user_id}')
            return

        if verify_signature(wallet_address, signature, SIGNING_MESSAGE.format(wallet_address)):
            if wallet_address.lower() not in whitelisted_addresses:
                logging.debug(f'Wallet address {wallet_address} is not whitelisted')
                return

            role = guild.get_role(int(ROLE_ID))
            if not role:
                logging.error(f'Role not found: {ROLE_ID}')
                return

            if role not in member.roles:
                await member.add_roles(role)
                logging.info(f'Role assigned to {user.name}')
            else:
                logging.debug(f'User {user.name} already has the role.')
        else:
            logging.debug(f'Signature verification failed for {user.mention}')
    except Exception as e:
        logging.error(f'Error in check_verification_logic: {e}')

def verify_signature(address, signature, message):
    try:
        encoded_message = encode_defunct(text=message)
        recovered_address = Account.recover_message(encoded_message, signature=signature)
        logging.debug(f'Recovered address: {recovered_address}')
        return recovered_address.lower() == address.lower()
    except Exception as e:
        logging.error(f'Error verifying signature: {e}')
        return False

@bot.event
async def on_ready():
    logging.info(f'Bot is ready. Logged in as {bot.user.name}')
    logging.debug(f'Bot ID: {bot.user.id}')

@bot.command(name='verify')
async def verify(ctx):
    try:
        logging.debug(f'!verify command invoked by user: {ctx.author.name}, ID: {ctx.author.id}')
        token = secrets.token_urlsafe(16)
        user_id = ctx.author.id
        pending_verifications[token] = user_id
        
        verification_link = f'{FRONTEND_URL}?token={token}'  # Send the URL with the token as a query parameter
        await ctx.author.send(f'To verify your wallet, please visit: {verification_link}')
        await ctx.send(f'{ctx.author.mention}, check your direct messages for the verification link.')
        logging.debug(f'Sent verification link to user: {ctx.author.name}')
    except Exception as e:
        logging.error(f'Error in verify command: {e}')
        await ctx.send('An error occurred during verification.')

@bot.event
async def on_message(message):
    if message.guild is None:  # Check if message is a DM
        await bot.process_commands(message)
    else:
        await bot.process_commands(message)

def run_flask():
    app.run(debug=True, use_reloader=False, host=ADDR, port=PORT)

if __name__ == '__main__':
    # Fetch whitelist before starting the bot and flask
    fetch_whitelist()
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    bot.run(TOKEN)