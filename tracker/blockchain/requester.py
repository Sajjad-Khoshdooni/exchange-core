from abc import ABC, abstractmethod

from tracker.blockchain.dtos import BlockDTO


class Requester(ABC):

    @abstractmethod
    def get_latest_block(self) -> BlockDTO:
        pass

    @abstractmethod
    def get_block_by_id(self, _hash: str) -> BlockDTO:
        pass

    @abstractmethod
    def get_block_by_number(self, number: int) -> BlockDTO:
        pass
