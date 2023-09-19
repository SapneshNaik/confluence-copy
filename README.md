# Confluence Copier
 _A command line tool to migrate documents from one Confluence instance to another._

## Features
- Update an existing page in your destination Confluence with content from a page in source confluence
- Copy a document from your source Confluence to destination Confluence
- Create a new page in your destination Confluence
- Copy entire space from source Confluence to destination Confluence

## Installation and Setup
Confluence Copier requires `Python 3+` to run.

1. Download the source code to your local machine where Python is installed.
2. Install requirements from the `requirements.txt` using `pip install -r requirements.txt`.
3. Rename `.env.example` to `.env` and update your source and destination Confluence credentials. 
4. Obtain a token here: https://id.atlassian.com/manage-profile/security/api-tokens. Make sure to generate a token each for your source and destination Confluence and update it accordingly in the `.env` file.

### `.env` configuration
```sh 
    SOURCE_CONFLUENCE_LINK="https://domain.net/wiki/rest/api/"
    SOURCE_CONFLUENCE_USERNAME="<email>"
    SOURCE_CONFLUENCE_API_TOKEN="<token>"

    DESTINATION_CONFLUENCE_LINK="https://domain.net/wiki/rest/api/"
    DESTINATION_CONFLUENCE_USERNAME="<email>"
    DESTINATION_CONFLUENCE_API_TOKEN="<token>"
```

## Supported Commands

| Command | Details |
| ------ | ------ |
| `copy-page`  | Copy page from source Confluence to destination Confluence |
| `copy-space` | Copy entire space from source Confluence to destination Confluence **[In Development]** |
| `create-new-page` | Create a new page in destination Confluence. |
| `update-page` | Update an existing page in destination Confluence with content from a page in source Confluence |

![Supported Commands](<assets/supported-commands.png>)

### Copy Page
Copy page from source Confluence to destination Confluence

**Usage:** 
```sh
python main.py copy-page --source-id="<source document id>" --parent-id="<destination parent document id>" --destination-space-key="<destination space key>" --new-doc-title="<new optional title>"
```
**Options:**
| Option Name|Data Type | Details |
| ------ | ------ | ------ |
|`--source-id`|TEXT|Page id in source Confluence.  [required]|
|`--destination-space-key`| TEXT | Space key in destination Confluence. [required]|
|`--parent-id`|INTEGER|  Parent document id in destination Confluence. Pass `-1` to create new document at root level of the space [required]|
|`--new-doc-title`| TEXT|  New doc name in destination Confluence. [Optional, uses the same name of the source document if not passed]|

**Example 1**
```sh
python main.py copy-page --source-id="123414" --parent-id="12312423" --destination-space-key="TEST"
```

**Example 2**
```sh
python main.py copy-page --source-id="123414" --parent-id="12312423" --destination-space-key="TEST" --new-doc-title="test-name"
```
**Screenshot**
![Copy Page](<assets/copy-page.png>)

## License

MIT

**Free Software, Hell Yeah!**
