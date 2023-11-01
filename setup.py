# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

package_data = {"": ["*"]}

install_requires = ["python-box==7.0.0", "restfly==1.4.7"]

setup_kwargs = {
    "name": "zscaler-sdk-python",
    "version": "1.0.0",
    "description": "Framework for interacting with Zscaler Cloud via API",
    "long_description": "# Zscaler SDK Python for the Zscaler API\n\n[![CI/CD](https://github.com/zscaler/zscaler-sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/zscaler/zscaler-sdk-python/actions/workflows/ci.yml)\n[![License](https://img.shields.io/github/license/zscaler/zscaler-sdk-python.svg)](https://github.com/zscaler/zscaler-sdk-python)\n[![Code Quality](https://app.codacy.com/project/badge/Grade/d339fa5d957140f496fdb5c40abc4666)](https://www.codacy.com/gh/zscaler/zscaler-sdk-python/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=zscaler/zscaler-sdk-python&amp;utm_campaign=Badge_Grade)\n[![PyPI Version](https://img.shields.io/pypi/v/zscaler.svg)](https://pypi.org/project/zscaler-sdk-python)\n[![PyPI pyversions](https://img.shields.io/pypi/pyversions/zscaler.svg)](https://pypi.python.org/pypi/zscaler-sdk-python/)\n[![GitHub Release](https://img.shields.io/github/release/zscaler/zscaler-sdk-python.svg)](https://github.com/zscaler/zscaler-sdk-python/releases/)\n\nZscaler SDK Python is an SDK that provides a uniform and easy-to-use interface for each of the Zscaler product APIs.\n\n## Quick links\n* [Zscaler SDK Python API Documentation](https://zscaler-sdk-python.readthedocs.io)\n\n## Overview\nEach Zscaler product has separate developer documentation and authentication methods. This SDK simplifies\nsoftware development using the Zscaler API.\n\nNote: This SDK was built off the amazing [pyZscaler](https://github.com/mitchos/pyZscaler) project created by [Mitch Kelly](https://github.com/mitchos)\n\nThis SDK leverages the [RESTfly framework](https://restfly.readthedocs.io/en/latest/index.html) developed\nby Steve McGrath.\n\n## Features\n- Simplified authentication with Zscaler APIs.\n- Uniform interaction with all Zscaler APIs.\n- Uses [python-box](https://github.com/cdgriffith/Box/wiki) to add dot notation access to json data structures.\n- Zscaler API output automatically converted from CamelCase to Snake Case.\n- Various quality of life enhancements for object CRUD methods.\n\n## Products\n- Zscaler Private Access (ZPA)\n- Zscaler Internet Access (ZIA)\n\n## Installation\n\nThe most recent version can be installed from pypi as per below.\n\n    $ pip install zscaler-sdk-python\n\n## Usage\n\nBefore you can interact with any of the Zscaler APIs, you may need to generate API keys or retrieve tenancy information\nfor each product that you are interfacing with. Once you have the requirements and you have installed Zscaler SDK Python, you're ready to go.\n\n### Quick ZIA Example\n\n```python\nfrom zscaler import ZIA\nfrom pprint import pprint\n\nzia = ZIA(api_key='API_KEY', cloud='CLOUD', username='USERNAME', password='PASSWORD')\nfor user in zia.users.list_users():\n    pprint(user)\n```\n\n### Quick ZPA Example\n\n```python\nfrom zscaler import ZPA\nfrom pprint import pprint\n\nzpa = ZPA(client_id='CLIENT_ID', client_secret='CLIENT_SECRET', customer_id='CUSTOMER_ID')\nfor app_segment in zpa.app_segments.list_segments():\n    pprint(app_segment)\n```\n\n## Documentation\n### API Documentation\nZscaler SDK Python's API is fully 100% documented and is hosted at [ReadTheDocs](https://zscaler-sdk-python.readthedocs.io).\n\nThis documentation should be used when working with Zscaler SDK Python rather than referring to Zscaler's API reference.\nZscaler SDK Python makes some quality of life improvements to simplify and clarify arguments passed to Zscaler's API.\n\n## Is It Tested?\nYes! Zscaler SDK Python has a complete test suite that fully covers all methods within the ZIA and ZPA modules.\n\n## Contributing\n\nContributions to Zscaler SDK Python are absolutely welcome.\n\nPlease see the [Contribution Guidelines](https://github.com/zscaler/zscaler-sdk-python/blob/main/CONTRIBUTING.md) for more information.\n\n[Poetry](https://python-poetry.org/docs/) is currently being used for builds and management. You'll want to have\npoetry installed and available in your environment.\n\n## Issues\nPlease feel free to open an issue using [Github Issues](https://github.com/zscaler/zscaler-sdk-python/issues) if you run into any problems using Zscaler SDK Python.\n\n## License\nMIT License\n\n=======\n\nCopyright (c) 2023 [Zscaler](https://github.com/zscaler)\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the \"Software\"), to deal\nin the Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons to whom the Software is\nfurnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all\ncopies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\nSOFTWARE.\n",
    "author": "Zscaler Technology Alliances",
    "author_email": "zscaler-partner-labs@z-bd.com",
    "maintainer": "None",
    "maintainer_email": "None",
    "url": "https://github.com/zscaler/zscaler-sdk-python",
    "packages": find_packages(),
    "package_data": package_data,
    "install_requires": install_requires,
    "python_requires": ">=3.8,<4.0",
}


setup(**setup_kwargs)
