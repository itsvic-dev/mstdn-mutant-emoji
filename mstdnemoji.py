import os
import requests
from html.parser import HTMLParser
from requests_toolbelt.utils import formdata
from requests_toolbelt.multipart.encoder import MultipartEncoder


class InvalidSessionIDException(Exception):
    pass


class AdminClient:
    def __init__(self, instance, requests_session):
        self.instance: str = instance
        self.session: requests.Session = requests_session

    class AuthTokenParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.authenticity_token = None

        def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "input":
                have_token = False
                for key, value in attrs:
                    if key == "name" and value == "authenticity_token":
                        have_token = True
                    if key == "value" and have_token:
                        self.authenticity_token = value

    def get_authenticity_token(self, suffix='/new'):
        resp = self.session.get(f"https://{self.instance}/admin/custom_emojis{suffix}",
                                verify=not self.instance.endswith(".local"))
        text = resp.content.decode()
        parser = self.AuthTokenParser()
        parser.feed(text)
        if not parser.authenticity_token:
            raise InvalidSessionIDException("Couldn't find authenticity token. Are you sure you supplied the right "
                                            "Session ID?")
        return parser.authenticity_token

    def upload_emoji(self, path: str, shortcode: str):
        # POST /admin/custom_emojis
        # authenticity_token (type: hidden) - god knows really
        # custom_emoji[shortcode] (type: string) - shortcode
        # custom_emoji[image] (type: file) - image (accepts png, gif, webp)
        _, ext = os.path.splitext(path)
        ext = ext.lstrip('.')
        if ext not in ('png', 'gif', 'webp'):
            raise Exception("File must be one of: png, gif, webp")
        encoder = MultipartEncoder({
            'authenticity_token': self.get_authenticity_token(),
            'custom_emoji[shortcode]': shortcode,
            'custom_emoji[image]': (path, open(path, 'rb'), f"image/{ext}")
        })
        resp = self.session.post(f"https://{self.instance}/admin/custom_emojis",
                                 verify=not self.instance.endswith(".local"), data=encoder,
                                 headers={'Content-Type': encoder.content_type}, allow_redirects=False)
        if resp.status_code != 302:
            raise Exception(resp.status_code)

    class PageCountParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.pages = None
            self._have_gap = False
            self._have_a = False

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "span":
                for key, value in attrs:
                    if key == "class" and value == "page gap":
                        self._have_gap = True
            if tag == "a" and self._have_gap:
                self._have_a = True

        def handle_data(self, data: str) -> None:
            if self._have_gap and self._have_a:
                self._have_gap = False
                self._have_a = False
                self.pages = int(data)

    def get_emoji_page_count(self):
        pages_resp = self.session.get(f"https://{self.instance}/admin/custom_emojis?local=1&page=1&shortcode=ms_",
                                      verify=not self.instance.endswith(".local"))
        parser = self.PageCountParser()
        parser.feed(pages_resp.content.decode())
        if not parser.pages:
            raise InvalidSessionIDException("Couldn't find total page count. Are you sure you supplied the right "
                                            "Session ID?")
        return parser.pages

    class EmojiIDParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.emojis = []

        def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "input":
                input_value = ""
                for key, value in attrs:
                    if key == "value":
                        input_value = value
                    if key == "name" and value == "form_custom_emoji_batch[custom_emoji_ids][]":
                        self.emojis.append(input_value)

    def delete_emoji_page(self):
        # POST /admin/custom_emojis/batch
        # authenticity_token (type: hidden) - god knows really
        # page (type: hidden) - page # we're on
        # local (type: hidden) - is local? (0/1)
        # shortcode (type: hidden) - shortcode search
        # batch_checkbox_all: (type: checkbox) - was the "all" checkbox checked?
        # delete (type: submit) - delete button, empty value
        # form_custom_emoji_batch[category_id] - category ID when assigning, empty value for us
        # form_custom_emoji_batch[category_name] - category name when assigning, empty value for us
        # form_custom_emoji_batch[custom_emoji_ids][] - emoji ID, repeated
        pages_resp = self.session.get(f"https://{self.instance}/admin/custom_emojis?local=1&page=1&shortcode=ms_",
                                      verify=not self.instance.endswith(".local"))
        parser = self.EmojiIDParser()
        parser.feed(pages_resp.content.decode())
        if not parser.emojis:
            raise Exception("Couldn't find any emojis.")
        data = formdata.urlencode([
            ('authenticity_token', self.get_authenticity_token("?local=1&page=1&shortcode=ms_")),
            ('page', '1'),
            ('local', '1'),
            ('shortcode', 'ms_'),
            ('batch_checkbox_all', 'on'),
            ('delete', ''),
            ('form_custom_emoji_batch[category_id]', ''),
            ('form_custom_emoji_batch[category_name]', ''),
            *[('form_custom_emoji_batch[custom_emoji_ids][]', emoji) for emoji in parser.emojis]
        ])
        resp = self.session.post(f"https://{self.instance}/admin/custom_emojis/batch",
                                 verify=not self.instance.endswith(".local"), data=data, allow_redirects=False,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        if resp.status_code != 302:
            raise Exception(resp.status_code)
