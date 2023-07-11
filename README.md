Confluence Copier
==============================

 A command line based tool to migrate documents from one Confluecne instance to another! 

# This document will be updated in the future.

How To Use This
---------------

1. Download the source code onto your local machine.
2. Install requirements from the requirements.txt using pip.
3. Run `pip install -r requirements.txt` to install dependencies
4. Rename `.env.example` to `.env` and update the source and destination Confluence credentials. You can obtain a token here: https://id.atlassian.com/manage-profile/security/api-tokens. Make sure to generate a token for each instance and update it accordingly in the `.env` file.
```
    SOURCE_CONFLUENCE_LINK="https://domain.net/wiki/rest/api/"
    SOURCE_CONFLUENCE_USERNAME="<email>"
    SOURCE_CONFLUENCE_API_TOKEN="<token>"

    DESTINATION_CONFLUENCE_LINK="https://domain.net/wiki/rest/api/"
    DESTINATION_CONFLUENCE_USERNAME="<email>"
    DESTINATION_CONFLUENCE_API_TOKEN="<token>"
```
4. The tool currently supports two commands, `update-page` and `copy-space`. 

Update-page
-------
