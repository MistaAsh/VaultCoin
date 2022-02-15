import datetime
import hashlib
import json
import requests

from flask import Flask, jsonify, request
from uuid import uuid4
from urllib.parse import urlparse

# Creating the Blockchain
class Blockchain:

    def __init__(self):
        self.chain = []
        self.mempool = []
        self.create_block(proof = 1, previous_hash = '0')
        self.nodes = set()

    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain) + 1,
                'timestamp': str(datetime.datetime.now()),
                'proof': proof,
                'previous_hash': previous_hash,
                'transactions': self.mempool}
        self.mempool = []
        self.chain.append(block)
        return block

    def get_last_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        leading_zeros = 4
        while not check_proof:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:leading_zeros] == '0'*leading_zeros:
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1 
        while block_index < len(chain):
            block = chain[block_index]
            if self.hash(previous_block) != block['previous_hash']:
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True
    
    def add_transaction(self, sender, receiver, amount):
        self.mempool.append({
            'sender': sender, 
            'receiver': receiver,
            'amount': amount
        })
        return self.get_last_block()['index'] + 1
    
    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
        
    # Consensus algorithm
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                local_chain = response.json()['chain']
                local_length = response.json()['length']
                
                if local_length > max_length and self.is_chain_valid(local_chain):
                    max_length = local_length
                    longest_chain = local_chain
                    
        if longest_chain:
            self.chain = longest_chain
            return True
        return False
        

# Flask-based WebApp to mine the blockchain
app = Flask(__name__)

# Creating an address for the node on Port 5000
node_address = str(uuid4()).replace('-', '')

# Creating a Blockchain instance
blockchain = Blockchain()

# Basic GET request
@app.route('/', methods=['GET'])
def home():
    return 'Welcome to the VaultCoin blockchain network !!'

# Mining a new block
@app.route('/mine_block', methods=['GET'])
def mine_block():
    previous_block = blockchain.get_last_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    blockchain.add_transaction(sender = node_address, receiver = 'Node1', amount = 10)

    block = blockchain.create_block(proof, previous_hash)
    response = {
        'Message': 'Congratulations! You have just mined a block :)',
        'index': block['index'],
        'timestamp': block['timestamp'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],        
        'transactions': block['transactions']
    }
    return jsonify(response), 200

# Getting the entire Blockchain
@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

# Checking for the validity of the Blockchain
@app.route('/is_valid', methods=['GET'])
def is_valid():
    check = blockchain.is_chain_valid(blockchain.chain)
    if check:
        response = {'message': 'Checks completed. The Blockchain is valid!'}
    else:
        response = {'message': 'Checks failed. The Blockchain is invalid!'}
    return jsonify(response), 200

# Adding a transaction to the Blockchain (mempool)
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    
    if not all (key in json for key in transaction_keys):
        return 'Error: Missing key values!', 400
    index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    response = {'message': f'Transaction successful! Transaction added to Block {index}',}
    return jsonify(response), 201

# Decentralizing the Blockchain

# Connecting new nodes to the network
@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return 'Error. No node!', 400
    for node in nodes:
        blockchain.add_node(node)
    response = {
        'message': 'Nodes successfully added to the blockchain network',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

# Replacing the chain by the longest chain if needed
@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    check = blockchain.replace_chain()
    if check:
        response = {'message': 'Chains different. Local Blockchain updated!',
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'No updates available. Local chain is the longest!',
                    'local_unchanged_chain': blockchain.chain}
    return jsonify(response), 200

    
# Running the App
app.run(host = '0.0.0.0', port = 5001)