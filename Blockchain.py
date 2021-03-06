import hashlib
import json
#import threading
import multiprocessing as mp

class Blockchain:
    def __init__(self, id):
        self.id = id
        self.chain = []
        self.nonce = 0
        self._incomplete_transactions = []
        self.FLAG_MINING = False
        self.create_unsolved_block(None)
        self.mining_thread = None

    def start_mining_thread(self):
        self.FLAG_MINING = True
        #self.mining_thread = threading.Thread(target=self.proof_of_work)
        self.mining_thread = mp.Process(target=self.proof_of_work)
        self.mining_thread.start()

    def stop_mining_thread(self):
        self.FLAG_MINING = False
        if self.mining_thread:
            self.mining_thread.join()

    @property
    def incomplete_transactions(self):
        return self._incomplete_transactions

    @incomplete_transactions.setter
    def incomplete_transactions(self, transaction):
        """
        Observer pattern that keeps track on self._incomplete_transactions list.
        PoW is only triggered when there are incompleted transactions exist.
        If there is any new transaction added into the list, we start the PoW all over again.
        When a new block is generated, we clean the incomplete transaction list and shut down the PoW thread
        :param transaction:
        :return:
        """

        # clean transaction list after a block is generated.
        if not transaction:
            self.FLAG_MINING = False
            self._incomplete_transactions = []

        # add new transaction into incomplete_transaction and start PoW thread all over again
        else:
            self.stop_mining_thread()
            self._incomplete_transactions.append(transaction)
            self.nonce = 0
            self.unsolved_block['transactions'] = self._incomplete_transactions.copy()
            self.start_mining_thread()

    def reinitialise_for_next_block(self):
        self.nonce = 0
        self.unsolved_block = {}
        self.incomplete_transactions = []
        self.create_unsolved_block(self.hash(self.chain[-1]))

    def create_unsolved_block(self, previous_hash):
        self.nonce = 0
        self.unsolved_block = {
            'index': len(self.chain) + 1,
            'transactions': self.incomplete_transactions,
            'proof': self.nonce,
            'previous_hash': previous_hash,
            'block generator': self.id,
        }

    def new_block(self):
        """
        Create a new Block in the Blockchain
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        self.chain.append(self.unsolved_block)

    def hash(self, block):
        """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def new_transaction(self, transaction):
        """

        :param transaction:
        :return:
        """
        self.incomplete_transactions = transaction

    def proof_of_work(self):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """
        while self.FLAG_MINING and self.valid_proof(self.unsolved_block) is False:
            self.nonce += 1
            self.unsolved_block['proof'] = self.nonce
        if self.FLAG_MINING:
            self.new_block()
            self.reinitialise_for_next_block()

    def valid_proof(self, block):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        return self.hash(block)[:4] == "0000"

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        previous_block = chain[0]
        current_index = 0

        while current_index < len(self.chain):
            block = chain[current_index]

            if current_index != 0:
                if block['previous_hash'] != self.hash(previous_block):
                    return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(block):
                return False

            previous_block = block
            current_index += 1

        return True

    def resolve_conflicts_and_update_transactions(self, other_node):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        This function also removes the approved transactions and add new transactions into incomplete transaction list
        :return: <bool> True if our chain was replaced, False if not
        """

        # Check if the length is longer and the chain is valid
        if len(other_node.chain) > len(self.chain):  # and self.valid_chain(other_node.chain):
            self.stop_mining_thread()
            self.chain = other_node.chain.copy()
            self.create_unsolved_block(self.hash(self.chain[-1]))

            if other_node.incomplete_transactions:
                self.broadcast_transactions(other_node)

            if self.incomplete_transactions:
                for block in self.chain:
                    self.remove_approved_incomplete_transactions(block)

            if self.incomplete_transactions:
                self.start_mining_thread()

    def remove_approved_incomplete_transactions(self, block):
        if self.incomplete_transactions:
            for transaction in self.incomplete_transactions:
                if transaction in block['transactions']:
                    self.incomplete_transactions.remove(transaction)

    def broadcast_transactions(self, other_node):
        if other_node.incomplete_transactions:
            for transaction in other_node.incomplete_transactions:
                if transaction not in self.incomplete_transactions:
                    self.new_transaction(transaction)
