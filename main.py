from functools import partial
from itertools import repeat
import json
import logging
import os
import shutil
import requests
import re
import typer
from dotenv import load_dotenv
from multiprocessing.pool import ThreadPool
from requests.auth import HTTPBasicAuth
from typing_extensions import Annotated
from os import listdir
from os.path import isfile, join
from treelib import Node, Tree
from multiprocessing import Pool, cpu_count
from typing import Optional
from Page import Page


# init command line library
app = typer.Typer()

# configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# load env file vars
load_dotenv()

SOURCE_CONFLUENCE_LINK = os.getenv('SOURCE_CONFLUENCE_LINK')
SOURCE_CONFLUENCE_USERNAME = os.getenv('SOURCE_CONFLUENCE_USERNAME')
SOURCE_CONFLUENCE_API_TOKEN = os.getenv('SOURCE_CONFLUENCE_API_TOKEN')
DESTINATION_CONFLUENCE_LINK = os.getenv('DESTINATION_CONFLUENCE_LINK')
DESTINATION_CONFLUENCE_USERNAME = os.getenv('DESTINATION_CONFLUENCE_USERNAME')
DESTINATION_CONFLUENCE_API_TOKEN = os.getenv(
    'DESTINATION_CONFLUENCE_API_TOKEN')


def get_page_details(page_id: str, url: str, username: str, pwd: str):
    """
        fetch page body
    """
    logging.info("Reading Page Body of {} from {}".format(page_id, url))
    uri = "{}/content/{}?expand=body.storage,version,space".format(
        url, page_id)
    response = requests.request(
        "GET", uri, auth=HTTPBasicAuth(username, pwd))
    if not response.status_code == 200:
        raise Exception("Failed to read page body", response.text)
    return response.json()


def update_page_body(page_id: str, source_page_details: dict, url: str, username: str, pwd: str):
    """
        Update page body
    """
    verson_comment = "confluence-copier: SourceURL: {}, SourcePageID: {}, SourcePageVersion: {}, SourcePageSpace: {}, SourcePageName: {}, User: {}".format(
        source_page_details['_links']['base'], source_page_details['id'], source_page_details['title'], source_page_details['version']['number'], source_page_details['space']['name'], username)

    logging.info("Updating body of the page {} on {}".format(page_id, url))

    destination_page_details = get_page_details(
        page_id, DESTINATION_CONFLUENCE_LINK, DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN)

    uri = "{}/content/{}".format(
        url, page_id)

    payload = {
        "version": {
            "number": destination_page_details['version']['number']+1,
            "message": verson_comment
        },
        "type": "page",
        "body": {
            "storage": {
                "value": source_page_details['body']['storage']['value'],
                "representation": "storage"
            }
        },
        "metadata": {
            "properties": {
                "content-appearance-draft": {
                    "value": "full-width"
                },
                "content-appearance-published": {
                    "value": "full-width"
                }
            }
        },
        "title": destination_page_details['title']
    }

    headers = {
        'Content-Type': 'application/json',
    }

    response = requests.request(
        "PUT", uri, headers=headers, auth=HTTPBasicAuth(username, pwd), data=json.dumps(payload))
    if not response.status_code == 200:
        raise Exception("Failed to update page body", response.text)
    return True


def get_attachment_list(page_id: str, url: str, username: str, pwd: str):
    """
        fetch list of attachments per page
    """
    logging.info("Read page attachments (image, GIF, Videos, file, etc) of {} from {}".format(
        page_id, url))

    attachments_uri = "{}/content/{}/child/attachment?limit=100000".format(
        url, page_id)
    response = requests.request(
        "GET", attachments_uri, auth=HTTPBasicAuth(username, pwd))
    if not response.status_code == 200:
        raise Exception("Failed to read page attachments", response.text)
    return response.json()['results']


def download_file(attachment, temp_folder, page_id: str, url: str, username: str, pwd: str):
    logging.info(
        "Downloading attachment {} - {} from {}".format(attachment['id'], attachment['title'], url))
    download_uri = "{}/content/{}/child/attachment/{}/download".format(
        url, page_id, attachment['id'])

    response = requests.request(
        "GET", download_uri, auth=HTTPBasicAuth(username, pwd))

    if not response.status_code == 200:
        logging.error("Could not download {} with id {}".format(
            attachment['title'], attachment['id']))
        logging.error(response.text)
        # raise Exception("Failed to download attachment {} - {}".format(
        #     attachment['id'], attachment['title']), response.text)

    with open('{}/{}'.format(temp_folder, attachment['title']),
              'wb') as file:
        file.write(response.content)


def download_attachments(page_id: str, url: str, username: str, pwd: str):
    """
        Download page attachments
    """

    attachments = get_attachment_list(page_id, url, username, pwd)
    # print(attachments)
    logging.info("Found {} attachments for page {} on {}".format(
        len(attachments), page_id, url))

    if len(attachments) == 0:
        return

    temp_folder = "temp/{}".format(page_id)
    logging.info(
        "Downloading attachments to a temperory folder {}".format(temp_folder))
    os.makedirs(temp_folder, exist_ok=True)

    pool = Pool(cpu_count())

    pool.map(partial(download_file, temp_folder=temp_folder,
                     page_id=page_id, url=url, username=username, pwd=pwd), attachments)
    # for attachment in attachments:
    #     download_file(attachment, temp_folder, page_id, url, username, pwd)


def upload_attachments(folder_id, page_id: str, url: str, username: str, pwd: str):
    """
        Upload previously downloaded source attachments to destination page.
    """

    temp_folder = "temp/{}".format(folder_id)

    if not os.path.exists(temp_folder):
        logging.info("No attachments for upload")
        return

    upload_uri = "{}/content/{}/child/attachment".format(
        url, page_id)

    file_names = [f for f in listdir(
        temp_folder) if isfile(join(temp_folder, f))]

    files = []
    for file in file_names:
        files.append(
            ('file', (file, open(
                '{}/{}'.format(temp_folder, file), 'rb'), 'application/octet-stream'))
        )

    if len(file_names) == 0:
        return

    logging.info("Uploading these {} attachments: {} from {} to page {} on {}".format(
        len(file_names), ", ".join(file_names), temp_folder, page_id, url))

    headers = {
        'X-Atlassian-Token': 'nocheck'
    }

    response = requests.request(
        "POST", upload_uri, auth=HTTPBasicAuth(username, pwd), headers=headers, files=files)

    if not response.status_code == 200:
        raise Exception("Failed to upload attachment {} - {}".format(
            file, page_id), response.text)

    logging.info("Uploaded {} to page {} on {}".format(
        file_names, page_id, url))


def remove_page_attachments(page_id, url, username, pwd):
    """
        Remove a Confluecne page's attachments.
        Note: Use this operation with caution.
    """
    logging.info(
        "Fetching existing attachments to remove from {} ({})".format(page_id, url))

    attachments = get_attachment_list(page_id, url, username, pwd)

    logging.info("Found {} attachments".format(
        len(attachments)))

    if len(attachments) == 0:
        return

    for attachment in attachments:
        logging.info("Deleting attachment {} - {} ({})".format(
            attachment['id'], attachment['title'], url))
        delete_uri = "{}/content/{}".format(url, attachment['id'])
        response = requests.request(
            "DELETE", delete_uri, auth=HTTPBasicAuth(username, pwd))
        if not response.status_code == 204:
            raise Exception("Failed to delete attachment {} - {} ({})".format(
                attachment['id'], attachment['title'], url))


def cleanup_temp_files():
    """
        Delete the temp folder
    """
    logging.info("Deleting the temp folder")
    if not os.path.exists('temp'):
        logging.info("No attachments for upload")
        return
    shutil.rmtree('temp')


def get_space_documents_recursively(space_key, url, username, pwd):
    """
        Recursively get list of documents in a space.
    """

    logging.info("Reading space hierarchy: {} from {}".format(space_key, url))

    attachments_uri = "{}/content?type=page&spaceKey={}&status=current&limit=20000&expand=ancestors,descendants.page".format(
        url, space_key)
    response = requests.request(
        "GET", attachments_uri, auth=HTTPBasicAuth(username, pwd))
    if not response.status_code == 200:
        raise Exception("Failed to read page attachments", response.text)
    data = response.json()['results']

    # init space tree
    tree = Tree()

    tree.create_node(space_key, space_key)

    # loop over list of pages.
    for page in data:
        if len(page['ancestors']) == 0:  # root node
            node = tree.get_node(page['id'])

            if node is None:
                tree.create_node(page['title'], page['id'],
                                 parent=space_key, data=Page(page))
        else:
            """
                leaf node. has ancestor info in order. We loop over every ancenstor, 
                add it as a node and then add the current page as a child to the last/nearest ancestor.
            """
            for counter, ancestor in enumerate(page['ancestors']):
                # farthest ancestor has root as parent, else the parent will be the previous entry in the ancestors array.
                parent = space_key if counter == 0 else page['ancestors'][(
                    counter-1)]['id']
                parent_node = tree.get_node(ancestor['id'])

                # add parent node only if not visited/added before.
                if parent_node is None:
                    tree.create_node(ancestor['title'],
                                     ancestor['id'], parent=parent, data=Page(ancestor))

            child_node = tree.get_node(page['id'])

            # add leaf node only if not visited/added before.
            if child_node is None:
                tree.create_node(page['title'], page['id'],
                                 parent=page['ancestors'][-1]['id'], data=Page(page))

    tree.show(sorting=True,
              key=lambda x: x.data.page_data['extensions']['position'])


def create_space(space_name, url, username, pwd):
    """
        Create a new space.
    """
    uri = "{}space".format(url)

    # generate space key from space name, format: https://support.atlassian.com/confluence-cloud/docs/choose-a-space-key/
    pattern = re.compile('[\W_]+')
    space_key = pattern.sub('', space_name)

    payload = {
        "key": space_key,
        "name": space_name,
        "description": {
            "plain": {
                "value": "Confluence-copier - User: {}".format(username),
                "representation": "plain"
            }
        }
    }

    headers = {
        'X-Atlassian-Token': 'nocheck',
        'Content-Type': 'application/json'
    }

    response = requests.request(
        "POST", uri, auth=HTTPBasicAuth(username, pwd), headers=headers, data=json.dumps(payload))

    if not response.status_code == 200:
        raise Exception("Failed to create space {} - {}".format(
            space_name, space_key), response.text)

    logging.info("Created new create space key: {}, name:{}".format(
        space_name, space_key))

    return space_key


def create_page(space_key, parent_id, url, username, pwd, document_name):
    """
        Create new document
    """

    uri = "{}content".format(url)

    payload = {
        "space": {
            "key": space_key
        },
        "type": "page",
        "title": document_name,
        "body": {
            "storage": {
                "value": "Document created using Confluence Copier",
                "representation": "wiki"
            }
        }}

    if parent_id != -1:
        payload['ancestors'] = []
        payload['ancestors'].append({"id": str(parent_id)})

    headers = {
        'X-Atlassian-Token': 'nocheck',
        'Content-Type': 'application/json'
    }

    response = requests.request(
        "POST", uri, auth=HTTPBasicAuth(username, pwd), headers=headers, data=json.dumps(payload))

    if not response.status_code == 200:
        raise Exception("Failed to create document {} in space {} under parent {} in destination Confluence".format(
            document_name, space_key, parent_id if parent_id != -1 else "ROOT"), response.text)

    logging.info("Created new document \"{}\" with id {} under parent {}".format(
        document_name, response.json()['id'], parent_id if parent_id != -1 else "ROOT"))

    return response.json()['id']


def get_document_name(document_id, url, username, password):
    """
        Create page name
    """

    uri = "{}content/{}".format(url, document_id)

    headers = {
        'X-Atlassian-Token': 'nocheck',
        'Content-Type': 'application/json'
    }

    response = requests.request(
        "GET", uri, auth=HTTPBasicAuth(username, password), headers=headers)

    if not response.status_code == 200:
        raise Exception("Failed to get document name {}".format(
            document_id), response.text)

    return response.json()['title']


@app.command()
def update_page(source_id: Annotated[str, typer.Option(help="Page id in source Confluence.")],
                destination_id: Annotated[str, typer.Option(help="Page id in destination Confluence.")]):
    """
        Update an existing page in destination Confluence with a page from source Confluence
    """
    source_page_details = get_page_details(
        source_id, SOURCE_CONFLUENCE_LINK, SOURCE_CONFLUENCE_USERNAME, SOURCE_CONFLUENCE_API_TOKEN)

    # Download attachments from source page
    download_attachments(source_id, SOURCE_CONFLUENCE_LINK,
                         SOURCE_CONFLUENCE_USERNAME, SOURCE_CONFLUENCE_API_TOKEN)

    # Remove attachments from destination page
    remove_page_attachments(destination_id, DESTINATION_CONFLUENCE_LINK,
                            DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN)

    # # upload previously downloaded attachments to destination page
    upload_attachments(source_id, destination_id, DESTINATION_CONFLUENCE_LINK,
                       DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN)

    # #Update destination page body
    update_page_body(destination_id, source_page_details, DESTINATION_CONFLUENCE_LINK,
                     DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN)

    # Remove previosuly downloaded files from local folder
    cleanup_temp_files()

    logging.info("Update operation completed!")


@app.command()
def copy_space(source_space_key: Annotated[str, typer.Option(help="Space key in source Confluence.")],
               destination_new_space_name: Annotated[str, typer.Option(help="New space name in destination Confluence.")]):
    """
        Copy entire space from source Confluence to destination Confluence
    """
    # get space docs
    # upload space docs one by one including attachments and as new pages with hierarchy

    get_space_documents_recursively(
        source_space_key, SOURCE_CONFLUENCE_LINK, SOURCE_CONFLUENCE_USERNAME, SOURCE_CONFLUENCE_API_TOKEN)

    # space_key = create_space(destination_new_space_name, DESTINATION_CONFLUENCE_LINK,
    #              DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN)


@app.command()
def create_new_page(space_key: Annotated[str, typer.Option(help="Space key in destination Confluence.")],
                    parent_id: Annotated[int, typer.Option(help="Parent document id in destination Confluence. Pass -1 to create new document at root level")],
                    doc_name: Annotated[str, typer.Option(help="New doc name in destination Confluence.")]):
    """
        Create a new page in destination Confluence.
    """
    # get space docs
    # upload space docs one by one including attachments and as new pages with hierarchy

    create_page(space_key, parent_id, DESTINATION_CONFLUENCE_LINK,
                DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN, doc_name)


@app.command()
def copy_page(source_id: Annotated[str, typer.Option(help="Page id in source Confluence.")],
              parent_id: Annotated[int, typer.Option(help="Parent document id in destination Confluence. Pass -1 to create new document at root level")],
              destination_space_key: Annotated[str, typer.Option(help="Space key in destination Confluence.")],
              new_doc_title: Annotated[Optional[str], typer.Option(help="New doc name in destination Confluence.")] = None,
              ):
    """
        Copy page from source Confluence to destination Confluence
    """

    if new_doc_title is None:
        new_doc_title = get_document_name(source_id, SOURCE_CONFLUENCE_LINK,
                                 SOURCE_CONFLUENCE_USERNAME, SOURCE_CONFLUENCE_API_TOKEN)

    logging.info("Copying document {} - {} from {} to {}".format(new_doc_title,
                 source_id, SOURCE_CONFLUENCE_LINK, DESTINATION_CONFLUENCE_LINK))

    doc_id = create_page(destination_space_key, parent_id, DESTINATION_CONFLUENCE_LINK,
                         DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN, new_doc_title)

    source_page_details = get_page_details(
        source_id, SOURCE_CONFLUENCE_LINK, SOURCE_CONFLUENCE_USERNAME, SOURCE_CONFLUENCE_API_TOKEN)

    # Download attachments from source page
    download_attachments(source_id, SOURCE_CONFLUENCE_LINK,
                         SOURCE_CONFLUENCE_USERNAME, SOURCE_CONFLUENCE_API_TOKEN)

    # Remove attachments from destination page TODO: May be reduandant
    remove_page_attachments(doc_id, DESTINATION_CONFLUENCE_LINK,
                            DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN)

    # # upload previously downloaded attachments to destination page
    upload_attachments(source_id, doc_id, DESTINATION_CONFLUENCE_LINK,
                       DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN)

    # #Update destination page body
    update_page_body(doc_id, source_page_details, DESTINATION_CONFLUENCE_LINK,
                     DESTINATION_CONFLUENCE_USERNAME, DESTINATION_CONFLUENCE_API_TOKEN)

    # Remove previosuly downloaded files from local folder
    cleanup_temp_files()

    logging.info("Copy operation completed!")


if __name__ == "__main__":
    app()
