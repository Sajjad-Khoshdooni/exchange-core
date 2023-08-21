from django.utils.baseconv import base64

from accounts.models import User, FinotechRequest
from accounts.verifiers.finotech import ServerError

from typing import Union
from dataclasses import dataclass

from decouple import config
from urllib3.exceptions import ReadTimeoutError
import requests
import logging

logger = logging.getLogger(__name__)


@dataclass
class MatchingData:
    is_matched: bool
    code: str


@dataclass
class CardInfoData:
    owner_name: str
    code: str
    bank_name: str = ''
    card_type: str = ''
    deposit_number: str = ''
    card_pan: str = ''


@dataclass
class IBANInfoData:
    bank_name: str
    owners: list
    code: str
    deposit_number: str = ''
    deposit_status: str = ''


@dataclass
class NationalIdentityData:
    is_matched: bool
    first_name: str
    last_name: str
    father_name: str
    is_alive: bool
    code: str


@dataclass
class CardToIBANData:
    owner_name: str
    IBAN: str
    bank_name: str
    code: str


@dataclass
class Address:
    province: str
    town: str
    district: str
    street: str
    street2: str
    number: int
    floor: str
    side_floor: str
    building_name: str
    description: str


@dataclass
class PostalToAddressData:
    address: Address
    code: str


@dataclass
class CardToAccountData:
    owner_name: str
    bank_name: str
    bank_account: str
    code: str


@dataclass
class Person:
    first_name: str
    last_name: str
    national_code: str
    nationality: str
    person_type: str
    position: str


@dataclass
class CompanyInformation:
    national_id: str
    title: str
    registration_id: str
    establishment_date: str
    address: str
    postal_code: str
    type: str
    status: str
    description: str
    related_people: list
    code: str


@dataclass
class PersianNameToEnglishData:
    english_name: str
    code: str


@dataclass
class NationalCard:
    first_name: str
    last_name: str
    father_name: str
    national_code: str
    birth_date: str
    expiration_date: str
    face_photo: base64
    city: str
    province: str
    code: str


@dataclass
class Response:
    data: Union[dict, list, MatchingData, CardInfoData, IBANInfoData]
    service: str
    success: bool = True
    status_code: int = 200

    def get_success_data(self):
        if not self.success:
            raise ServerError

        return self.data


class ZibalRequester:
    BASE_URL = 'https://api.zibal.ir'

    RESULT_MAP = {
        1: 'SUCCESSFUL',
        2: 'INVALID_API_KEY',
        3: 'WRONG_API_KEY',
        4: 'PERMISSION_DENIED',
        5: 'INVALID_CALL_BACK_URL',
        6: 'INVALID_DATA',
        7: 'INVALID_IP',
        8: 'INACTIVE_API_KEY',
        9: 'LOWER_THAN_MINIMUM_AMOUNT',
        21: 'INVALID_IBAN',
        29: 'INSUFFICIENT_FUNDING',
        44: 'IBAN_NOT_FOUND',
        45: 'SERVICE_UNAVAILABLE'
    }

    def __init__(self, user: User):
        self._user = user

    def collect_api(self, path: str, method: str = 'GET', data=None, weight: int = 0) -> Response:
        if data is None:
            data = {}
        url = self.BASE_URL + path

        req_object = FinotechRequest(
            url=url,
            method=method,
            data=data,
            user=self._user,
            service=FinotechRequest.ZIBAL,
            weight=weight,
        )

        request_kwargs = {
            'url': url,
            'timeout': 30,
            'headers': {'Authorization': config('ZIBAL_KYC_API_TOKEN')}
        }

        try:
            if method == 'GET':
                resp = requests.get(params=data, **request_kwargs)
            else:
                method_prop = getattr(requests, method.lower())
                resp = method_prop(json=data, **request_kwargs)

        except (requests.exceptions.ConnectionError, ReadTimeoutError, requests.exceptions.Timeout):
            req_object.response = 'timeout'
            req_object.status_code = 100
            req_object.save()

            logger.error('zibal connection error', extra={
                'path': path,
                'method': method,
                'data': data,
            })
            raise TimeoutError

        resp_data = resp.json()
        req_object.response = resp_data
        req_object.status_code = resp.status_code
        req_object.save()

        if resp.status_code >= 500:
            logger.error('failed to call zibal', extra={
                'path': path,
                'method': method,
                'data': data,
                'resp': resp_data,
                'status': resp.status_code
            })
            raise ServerError

        return Response(data=resp_data, status_code=resp.ok, service='ZIBAL')

    def matching(self, phone_number: str = None, national_code: str = None) -> Response:
        params = {
            "mobile": phone_number,
            "nationalCode": national_code
        }

        resp = self.collect_api(
            data=params,
            path='/v1/facility/shahkarInquiry',
            method='POST',
            weight=FinotechRequest.JIBIT_ADVANCED_MATCHING if national_code else FinotechRequest.JIBIT_SIMPLE_MATCHING
        )
        data = resp.data.get('data', {})
        resp.data = MatchingData(
            is_matched=data.get('matched', ''),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def get_iban_info(self, iban: str) -> Response:
        params = {
            "IBAN": iban,
        }
        resp = self.collect_api(
            data=params,
            path='/v1/facility/ibanInquiry',
            method='POST',
            weight=FinotechRequest.JIBIT_IBAN_INFO_WEIGHT,
        )
        data = resp.data.get('data', {})
        resp.data = IBANInfoData(
            bank_name=data.get('bankName', ''),
            owners=data.get('name', ''),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def get_card_info(self, card_pan: str) -> Response:
        params = {
            "cardNumber": card_pan,
        }
        resp = self.collect_api(
            path='/v1/facility/cardInquiry',
            method='POST',
            data=params,
            weight=FinotechRequest.JIBIT_CARD_INFO_WEIGHT
        )
        data = resp.data.get('data', {})
        resp.data = CardInfoData(
            owner_name=data.get('name', ''),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    # todo: adjust weights & define data class for responses

    def national_identity_matching(self, national_code: str, birth_date: str):
        params = {
            "nationalCode": national_code,
            "birthDate": birth_date  # todo check format: "1374/11/23"
        }
        resp = self.collect_api(
            path="/v1/facility/nationalIdentityInquiry",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = NationalIdentityData(
            is_matched=data.get('matched', False),
            first_name=data.get('firstName', ''),
            last_name=data.get('lastName', ''),
            father_name=data.get('fatherName', ''),
            is_alive=data.get('alive', False),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def card_to_iban(self, card_pan: str):
        params = {
            "cardNumber": card_pan
        }
        resp = self.collect_api(
            path="/v1/facility/cardToIban",
            method='POST',
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = CardToIBANData(
            owner_name=data.get('name', ''),
            IBAN=data.get('IBAN', ''),
            bank_name=data.get('bankName', ''),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    # todo: ask about the format
    def postal_code_to_address(self, postal_code: str):
        params = {
            "postalCode": postal_code
        }
        resp = self.collect_api(
            path="/v1/facility/postalCodeInquiry",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = PostalToAddressData(
            Address(
                province=data.get('province', ''),
                town=data.get('town', ''),
                district=data.get('district', ''),
                street=data.get('street', ''),
                street2=data.get('street2', ''),
                number=data.get('number', 0),
                floor=data.get('floor', ''),
                side_floor=data.get('sideFloor', ''),
                building_name=data.get('buildingName', ''),
                description=data.get('description', '')
            ),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def iban_owner_matching(self, iban: str, name: str):
        params = {
            "IBAN": iban,
            "name": name
        }
        resp = self.collect_api(
            path="/v1/facility/checkIBANWithName",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = MatchingData(
            is_matched=data.get('matched', False),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def card_owner_matching(self, card_pan: str, name: str):
        params = {
            "cardNumber": card_pan,
            "name": name
        }
        resp = self.collect_api(
            path="/v1/facility/checkCardWithName",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = MatchingData(
            is_matched=data.get('matched', False),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    # todo: check account name on project
    def card_to_account(self, card_number: str):
        params = {
            "cardNumber": card_number
        }
        resp = self.collect_api(
            path="/v1/facility/cardToAccount",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = CardToAccountData(
            owner_name=data.get('name', ''),
            bank_name=data.get('bankName', ''),
            bank_account=data.get('bankAccount', ''),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def national_code_card_matching(self, national_code: str, birth_date: str, card_number: str):
        params = {
            "nationalCode": national_code,
            "birthDate": birth_date,
            "cardNumber": card_number
        }
        resp = self.collect_api(
            path="/v1/facility/checkCardWithNationalCode",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = MatchingData(
            is_matched=data.get('matched', False),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def national_code_iban_matching(self, national_code: str, birth_date: str, iban: str):
        params = {
            "nationalCode": national_code,
            "birthDate": birth_date,
            "IBAN": iban
        }
        resp = self.collect_api(
            path="/v1/facility/checkIbanWithNationalCode",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = MatchingData(
            is_matched=data.get('matched', False),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def company_information(self, national_id: str):
        params = {
            "nationalId": national_id,
        }
        resp = self.collect_api(
            path="/v1/facility/companyInquiry",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = CompanyInformation(
            national_id=data.get('nationalId', ''),
            title=data.get('companyTitle', ''),
            registration_id=data.get('companyRegistrationId', ''),
            establishment_date=data.get('establishmentDate', ''),
            address=data.get('address', ''),
            postal_code=data.get('postalCode', ''),
            type=data.get('companyType', ''),
            status=data.get('status', ''),
            description=data.get('extraDescription', ''),
            related_people=[
                Person(
                    first_name=person.get('firstName', ''),
                    last_name=person.get('lastName', ''),
                    national_code=person.get('nationalCode', ''),
                    nationality=person.get('nationality', ''),
                    person_type=person.get('personType', ''),
                    position=person.get('officePosition', '')
                )
                for person in data.get('companyRelatedPeople', [])
            ],
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def persian_name_to_english(self, name: str):
        params = {
            "persianText": name
        }
        resp = self.collect_api(
            path="/v1/facility/persianToFinglish",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = PersianNameToEnglishData(
            english_name=data.get('finglishText', ''),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
        return resp

    def national_card_ocr(self, card_back: str, card_front: str):
        params = {
            'nationalCardFront': card_front,
            'nationalCardBack': card_back
        }
        resp = self.collect_api(
            path="/v1/facility/nationalCardOcr",
            method="POST",
            data=params
        )
        data = resp.data.get('data', {})
        resp.data = NationalCard(
            first_name=data.get('firstName', ''),
            last_name=data.get('lastName', ''),
            father_name=data.get('fatherName', ''),
            national_code=data.get('nationalCode', ''),
            birth_date=data.get('birthDate', ''),
            expiration_date=data.get('expirationDate', ''),
            face_photo=data.get('facePhoto', None),
            city=data.get('city', ''),
            province=data.get('province', ''),
            code=ZibalRequester.RESULT_MAP.get(resp.data.get('result', ''), '')
        )
