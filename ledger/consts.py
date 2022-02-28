DEFAULT_COIN_OF_NETWORK = {
    'BSC': 'BNB',
    'TRX': 'TRX',
    'ETH': 'ETH'
}

# https://support.binance.org/support/solutions/articles/67000666099-binance-peg-token-list
BEP20_SYMBOL_TO_SMART_CONTRACT = {
    'ETH': '0x2170ed0880ac9a755fd29b2688956bd959f933f8', 'BTC': '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c',
    'USDT': '0x55d398326f99059ff775485246999027b3197955',
    'SOL': '0x570a5d26f7765ecb712c0924e4de545b89fd43df', 'SHIB': '0x2859e4544c4bb03966803b044a93563bd2d0dd4d',
    'AAVE': '0xfb6115445bff7b52feb98650c87f44907e58f802', 'UNI': '0xbf5140a22578168fd562dccf235e5d43a02ce9b1',
    'LINK': '0xf8a0bf9cf54bb92f17374d9e9a321e6a111a51bd', 'DOGE': '0xba2ae424d960c26247dd6c32edc70b295c744c43',
    'ADA': '0x3ee2200efb3400fabb9aacf31297cbdd1d435d47', 'FTM': '0xad29abb318791d579433d831ed122afeaf29dcfe',
    'BCH': '0x8ff795a6f4d97e7887c79bea79aba5cc76444adf', 'XRP': '0x1d2f0da169ceb9fc7b3144628db156f3f6c60dbe',
    'EOS': '0x56b6fb708fc5732dec1afc8d8556423a2edccbd6', 'LTC': '0x4338665cbb7b2485a8855a139b75d5e34ab0db94',
    'TRX': '0x85eac5ac2f758618dfa09bdbe0cf174e7d574d5b', 'ETC': '0x3d6545b08693dae087e957cb1180ee38b9e3c25e',
    'XLM': '0x43c934a845205f0b514417d757d7235b8f53f1b9', 'DOT': '0x7083609fce4d1d8dc0c979aab8c869ea2c873402',
    'ZEC': '0x1ba42e5193dfa8b03d15dd1b86a3113bbbef8eeb', 'XTZ': '0x16939ef78684453bfdfb47825f8a5f714f12623a',
    'ATOM': '0x0eb3a705fc54725037cc9e008bdede697f62f335', 'BAT': '0x101d82428437127bf1608f699cd651e6abf9766e',
    'ZIL': '0xb86abcb37c3a4b64f74f59301aff131a1becc787', 'COMP': '0x52ce071bd9b1c4b00a0b92d298c512478cad67e8',
    'SXP': '0x47bead2563dcbf3bf2c9407fea4dc236faba485a', 'MKR': '0x5f0da599bb2cccfcf6fdfd7d81743b6020864350',
    'SNX': '0x9ac983826058b8a9c7aa1c9171441191232e8404', 'YFI': '0x88f1a5ae2a3bf98aeaf342d26b30a79438c9142e',
    'SUSHI': '0x947950bcc74888a40ffa2593c5798f11fc9124c4', 'EGLD': '0xbf7c81fff98bbe61b40ed186e4afd6ddd01337fe',
    'AVAX': '0x1ce0c2827e2ef14d5c4f29a091d735a204794041', 'FIL': '0x0d8ce2a99bb6e3b7db580ed848240e4a0f9ae153',
    'MATIC': '0xcc42724c6683b7e57334c4e856f4c9965ed682bd', 'AXS': '0x715d400f88c167884bbcc41c5fea407ed4d2f8a0',
    '1INCH': '0x111111111117dc0aa78b770fa6a738034120c302', 'ANKR': '0xf307910a4c7bbc79691fd374889b36d8531b08e3',
    'DODO': '0x67ee3cb086f8a16f34bee3ca72fad36f7db929e2', 'ALICE': '0xac51066d7bec65dc4589368da368b212745d63e8',
    'REEF': '0xf21768ccbc73ea5b6fd3c687208a7c2def2d966e', 'CELR': '0x1f9f6a696c6fd109cd3956f45dc709d2b3902163',
    'GALA': '0x7ddee176f665cd201f93eede625770e2fd911990',
}
    # ---------------------------------------------------------------------------------------------------------
BEP20_TMP = {
    'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c', 'USDC': '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d',
    'BUSD': '0xe9e7cea3dedca5984780bafc599bd69add087d56', 'UST': '0x23396cf899ca06c4472205fc903bdb4de249d6fc',
    'DAI': '0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3',
    'NEAR': '0x1fa4a73a3f0133f0025378af00236f3abdee5d63',
    'IOTA': '0xd944f1d1e9d5f9bb90b62f9d45e447d989580782',
    'FRAX': '0x90c97f71e18723b0cf0dfa30ee176ab653e89f40',
    'FLOW': '0xc943c5320b9c18c153d1e2d12cc3074bebfb31a2', 'BTT': '0x352Cb5E19b12FC216548a2677bD0fce83BaE434B',
    'XEC': '0x0ef2e7602add1733bfdb17ac3094d0421b502ca3',
    'TUSD': '0x14016e85a25aeb13065688cafb43044c2ef86784',
    'USDP': '0xb3c11196a4f3b1da7c23d9fb0a3dde9c6340934f',
    'IOTX': '0x9678e42cebeb63f23197d726b29b1cb20d0064e5', 'SFM': '0x42981d0bfbAf196529376EE702F2a9Eb9092fcB5',
    'PAX': '0xb7f8cd00c5a06c0537e2abff0b58033d02e5e094',
    'SLP': '0x070a08beef8d36734dd67a491202ff35a6a16d97',
    'FXS': '0xe48a3d7d0bc88d552f730b62c006bc925eadb9ee',
    'BNT': '0xa069008a669e2af00a86673d9d584cfb524a42cc', 'NFT': '0x1fc9004ec7e5722891f5f38bae7678efcb11d34d',
    'BabyDoge': '0xc748673057861a797275CD8A068AbB95A902e8de',
    'ONT': '0xfd7b3a77848f1c2d67e05e54d78d174a0c850335', 'ANY': '0xf68c9df95a18b2a5a5fa1124d79eeeffbad0b6fa',
    'WRX': '0x8e17ed70334c87ece574c9d537bc153d8609e2a3', 'JST': '0xea998d307aca04d4f0a3b3036aba84ae2e409c0a',
    'PAXG': '0x7950865a9140cb519342433146ed5b40c6f210f7', 'C98': '0xaec945e04baf28b135fa7c640f624f8d90f1c3a6',
    'TLOS': '0xb6c53431608e626ac81a9776ac3e999c5556717c',
    'CTSI': '0x8da443f84fea710266c8eb6bc34b71702d033ef2',
    'COTI': '0xadbaf88b39d37dc68775ed1541f1bf83a5a45feb',
    'TWT': '0x4b0f1812e5df2a09796481ff14017e6005508003', 'ELF': '0xa3f020a5c92e15be13caf0ee5c95cf79585eecc9',
    'KNC': '0xfe56d5892bdffc7bf58f2e84be1b2c32d21c308b', 'ALPHA': '0xa1faa113cbe53436df28ff0aee54275c13b40975',
    'bCFX': '0x045c4324039dA91c52C55DF5D785385Aab073DcF', 'vBTC': '0x882c173bc7ff3b7786ca16dfed3dfffb9ee7847b',
    'SUN': '0xa1e6c58d503e4eee986167f45a063853cefe08c3', 'PROM': '0xaf53d56ff99f1322515e54fdde93ff8b3b7dafd5',
    'BIFI': '0xCa3F508B8e4Dd382eE878A314789373D80A5190A', 'TLM': '0x2222227e22102fe3322098e4cbfe18cfebd57c95',
    'FEG': '0xacfc95585d80ab62f67a14c566c1b7a49fe91167', 'POLS': '0x7e624fa0e1c4abfd309cc15719b7e2580887f570',
    '$DG': '0x9fdc3ae5c814b79dca2556564047c5e7e5449c19', 'BAKE': '0xE02dF9e3e622DeBdD69fb838bB799E3F168902c5',
    'BAND': '0xad6caeb32cd2c308980a548bd0bc5aa4306c6c18', 'KOGE': '0xe6df05ce8c8301223373cf5b969afcb1498c5528',
    'vETH': '0xf508fcd89b8bd15579dc79a6827cb4686a3592c8', 'BTCST': '0x78650b139471520656b9e7aa7a5e9276814a38e9',
    'XVS': '0xcf6bb5389c92bdda8a3747ddb454cb7a64626c63', 'BZRX': '0x4b87642aedf10b642be4663db842ecc5a88bf5ba',
    'RFOX': '0x0a3a21356793b49154fd3bbe91cbc2a16c0457f5', 'EPS': '0xa7f552078dcc247c2684336020c03648500c6d9f',
    'FUSE': '0x5857c96dae9cf8511b08cb07f85753c472d36ea3', 'MIR': '0x5b6dcf557e2abe2323c48445e8cc948910d8c2c9',
    'vUSDC': '0xeca88125a5adbe82614ffc12d0db554e2e2867c8', 'RISE': '0x0cD022ddE27169b20895e0e2B2B8A33B25e63579',
    'SFP': '0xd41fdb03ba84762dd66a0af1a6c8540ff1ba5dfb', 'CTK': '0xa8c2b8eec3d368c0253ad3dae65a5f2bbb89c929',
    'ATA': '0xa2120b9e674d3fc3875f415a7df52e382f141225', 'YFII': '0x7f70642d88cf1c4a3a7abb072b53b929b653eda5',
    'SAITO': '0x3c6dad0475d3a1696b359dc04c99fd401be134da', 'QANX': '0xaaa7a10a8ee237ea61e8ac46c50a8db8bcc1baaa',
    'LTO': '0x857b222fc79e1cbbf8ca5f78cb133d1b7cf34bbd',
}

ERC20_SYMBOL_TO_SMART_CONTRACT = {
    'USDT': '0xdac17f958d2ee523a2206206994597c13d831ec7', 'BNB': '0xB8c77482e45F1F44dE1745F52C74426C631bDD52',
    'USDC': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', 'HEX': '0x2b591e99afe9f32eaa6214f7b7629768c40eeb39',
    'BUSD': '0x4fabb145d64652a948d72533023f6e7a623c7c53', 'SHIB': '0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE',
    'MATIC': '0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0', 'CRO': '0xa0b73e1ff0b80914ab6fe0444e65848c4c34450b',
    'UST': '0xa47c8bf37f92abed4a126bda807a7b7498661acd', 'WBTC': '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
    'DAI': '0x6b175474e89094c44da98b954eedeac495271d0f', 'LINK': '0x514910771af9ca656af840dff83e8264ecf986ca',
    'TRX': '0xe1be5d3f34e89de342ee97e6e90d405884da6c67', 'OKB': '0x75231f58b43240c9718dd58b4967c5114342a86c',
    'LEO': '0x2af5d2ad76741191d15dfe7bf6ac92d4bd912ca3', 'stETH': '0xae7ab96520de3a18e5e111b5eaab095312d7fe84',
    'wstETH': '0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0', 'THETA': '0x3883f5e181fccaf8410fa61e12b59bad963fb645',
    'FTM': '0x4e15361fd6b4bb609fa63c81a2be19d873717870', 'UNI': '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984',
    'wMANA': '0xfd09cf7cfffa9932e33668311c4777cb9db3c9be', 'SAND': '0x3845badAde8e6dFF049820680d1F14bD3903a5d0',
    'VEN': '0xd850942ef8811f2a866692a623011bde52a462c1', 'WFIL': '0x6e1A19F235bE7ED8E3369eF73b196C07257494DE',
    'cETH': '0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5', 'cDAI': '0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643',
    'cUSDC': '0x39aa39c021dfbae8fac545936693ac917d5e7563', 'MIM': '0x99d8a9c45b2eca8864373a26d1459e3dff1e17f3',
    'FRAX': '0x853d955acef822db058eb8505911ed77f175b99e', 'GRT': '0xc944e90c64b2c07662a292be6244bdf05cda44a7',
    'GALA': '0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', 'ONE': '0x799a4202c12ca952cb311598a024c80ed371a41e',
    'BTT': '0xc669928185dbce49d2230cc9b0979be6dc797957', 'MKR': '0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2',
    'QNT': '0x4a220e6096b25eadb88358cb44068a3248254675', 'ENJ': '0xf629cbd94d3791c9250152bd8dfbdf380e2a3b9c',
    'HBTC': '0x0316EB71485b0Ab14103307bf65a021042c6d380', 'HT': '0x6f259637dcd74c767781e37bc6133cd6a68aa161',
    'KCS': '0xf34960d9d60be18cc1d5afc1a6f012a723a28811', 'AMP': '0xff20817765cb7f73d4bde2e66e067e58d11095c2',
    'TUSD': '0x0000000000085d4780B73119b644AE5ecd22b376', 'CEL': '0xaaaebe6fe48e54f431b0c390cfaf0b017d09d42d',
    'wCELO': '0xe452e6ea2ddeb012e20db73bf5d3863a3ac8d77a', 'BAT': '0x0d8775f648430679a709e98d2b0cb6250d2887ef',
    'LRC': '0xbbbbca6a901c926f240b89eacb641d8aec7aeafd', 'NEXO': '0xb62132e35a6c13ee1ee0f84dc5d40bad8d815206',
    'SLP': '0xcc8fa225d80b9c7d42f96e9570156c65d6caaa25', 'aCRV': '0x8dae6cb04688c62d939ed9b68d32bc62e49970b1',
    'CHZ': '0x3506424f91fd33084466f402d5d97f05f8e3b4af', 'SNX': '0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f'
}
