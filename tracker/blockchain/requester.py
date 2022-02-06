from abc import ABC, abstractmethod


class Requester(ABC):

    @abstractmethod
    def get_latest_block(self):
        pass

    @abstractmethod
    def get_block_by_id(self, _hash):
        pass

    @abstractmethod
    def get_block_by_number(self, number):
        pass
