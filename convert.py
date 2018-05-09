#!/usr/bin/env python3

import base64
import logging
import os
import re
import sys
from hashlib import md5
from pathlib import Path
from typing import Dict, Iterator, List, NamedTuple, Optional, TextIO, Tuple
from xml.etree import ElementTree

import click
import html2text
import magic
import slugify


Note = NamedTuple('Note', [('title', str), ('content', str)])
Resource = NamedTuple('Resource', [('data', bytes)])

# Defines MIME type to file extension mapping.
EXTENSIONS = {
    'application/x-empty': 'txt',
    'image/gif': 'gif',
    'image/jpeg': 'jpeg',
    'image/png': 'png',
    'image/svg': 'svg',
    'image/svg+xml': 'svg',
    'image/x-ms-bmp': 'bmp',
    'application/pdf': 'pdf'
}


@click.command()
@click.argument('emex_file', type=click.File(encoding='utf-8'))
@click.argument('output_path', type=click.Path(file_okay=False, writable=True))
@click.option("-v", "--verbose", type=bool, is_flag=True, help='Increase log verbosity.')
def main(emex_file: TextIO, output_path: str, verbose: bool):
    """
    Evernote ENEX to Markdown converter.
    """
    logging.basicConfig(
        datefmt="%H:%M:%S",
        format="%(asctime)s %(message)s",
        level=(logging.INFO if verbose else logging.WARNING),
        stream=sys.stderr,
    )
    process_emex(emex_file, Path(output_path))


def process_emex(emex_file: TextIO, output_path: Path):
    relative_media_path = Path('media')
    media_path = output_path / relative_media_path

    logging.info('Creating target directories…')
    output_path.mkdir(parents=True, exist_ok=True)
    media_path.mkdir(parents=True, exist_ok=True)

    # Resources are referenced by their MD5 hashes. Here we store hash to path mapping.
    media_paths: Dict[str, Path] = {}

    for note, resource in iterate_emex(emex_file, media_paths):
        if note is not None:
            logging.info('Note: %s', note.title)
            file_path = output_path / f'{slugify.slugify(note.title)}{os.extsep}md'
            logging.info('Saving %s', file_path)
            file_path.write_text(note.content, encoding='utf-8')

        if resource is not None:
            # Saving the resource under the name constructed from the hash and extension.
            hex_digest = md5(resource.data).hexdigest()
            mime_type = magic.from_buffer(resource.data, mime=True)
            file_name = f'{hex_digest}{os.extsep}{EXTENSIONS[mime_type]}'
            file_path = media_path / file_name
            if not file_path.exists():
                logging.info('Saving %s', file_path)
                file_path.write_bytes(resource.data)
            else:
                logging.info('Already exists, skipping: %s', file_path)

            # Use relative path for Markdown.
            media_paths[hex_digest] = relative_media_path / file_name


def iterate_emex(emex_file: TextIO, media_paths: Dict[str, Path]) -> Iterator[Tuple[Optional[Note], Optional[Resource]]]:
    """
    Lazily iterates over notes and resources in the exported file.
    """
    title: str
    content: str
    data: bytes

    for _, element in ElementTree.iterparse(emex_file):
        if element.tag == 'title':
            title = element.text
        elif element.tag == 'content':
            content = element.text
        elif element.tag == 'data':
            data = base64.b64decode(element.text or '')
        elif element.tag == 'resource':
            yield None, Resource(data)
        elif element.tag == 'note':
            yield Note(title, ContentParser(media_paths).handle(content)), None
        element.clear()


class ContentParser(html2text.HTML2Text):
    """
    Parses ENML content.
    """

    def __init__(self, media_paths: Dict[str, Path]):
        super().__init__()
        self.media_paths = media_paths

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        attrs_dict = dict(attrs)

        if tag == 'en-note':
            pass  # skip
        elif tag == 'en-media':
            self.o(f'![{attrs_dict.get("title", "")}]({self.media_paths[attrs_dict["hash"]]})')
        elif tag == 'en-crypt':
            logging.error('<en-crypt> is not implemented.')
        elif tag == 'en-todo':
            self.o('[x]' if attrs_dict.get('checked') else '[ ]')
        else:
            return super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str):
        if tag in ('en-note', 'en-media', 'en-crypt', 'en-todo'):
            pass  # skip
        else:
            return super().handle_endtag(tag)

    def error(self, message: str):
        logging.error('HTML parsing error: %s', message)


if __name__ == '__main__':
    main()
