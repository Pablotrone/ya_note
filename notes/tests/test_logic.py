from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from pytils.translit import slugify

from notes.forms import WARNING
from notes.models import Note

User = get_user_model()

TITLE = 'Заголовок'
TEXT = 'Текст заметки'
SLUG = 'slug'


class TestNoteCreation(TestCase):
    """Тестирование логики создания заметок"""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Автор заметки')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.form_data = {
            'title': TITLE,
            'text': TEXT,
            'slug': SLUG,
        }
        cls.user = User.objects.create(username='Пользователь')

    def test_anonymous_user_cant_post_note(self):
        """Анонимный пользователь не может создать заметку"""
        url = reverse('notes:add')
        login_url = reverse('users:login')
        expected_url = f'{login_url}?next={url}'
        notes_count = Note.objects.count()
        response = self.client.post(url, data=self.form_data)
        self.assertRedirects(response, expected_url)
        notes_count_after_add = Note.objects.count()
        self.assertEqual(notes_count_after_add, notes_count)

    def test_auth_user_can_post_note(self):
        """Залогиненный пользователь может создать заметку"""
        url = reverse('notes:add')
        url_success = reverse('notes:success')
        notes_count = Note.objects.count()
        response = self.author_client.post(url, data=self.form_data)
        self.assertRedirects(response, url_success)
        notes_count_after_add = Note.objects.count()
        self.assertEqual(notes_count + 1, notes_count_after_add)
        note_value = Note.objects.last()
        self.assertEqual(note_value.title, TITLE)
        self.assertEqual(note_value.text, TEXT)
        self.assertEqual(note_value.slug, SLUG)
        self.assertEqual(note_value.author, self.author)

    def test_empty_slug(self):
        """Если при создании заметки не заполнен slug,

        то он формируется автоматически,
        с помощью функцииpytils.translit.slugify.
        """
        url = reverse('notes:add')
        url_success = reverse('notes:success')
        notes_count = Note.objects.count()
        self.form_data.pop('slug')
        response = self.author_client.post(url, data=self.form_data)
        self.assertRedirects(response, url_success)
        notes_count_after_add = Note.objects.count()
        self.assertEqual(notes_count + 1, notes_count_after_add)
        last_note = Note.objects.last()
        expected_slug = slugify(self.form_data['title'])
        self.assertEqual(last_note.slug, expected_slug)

    def test_not_unique_slug(self):
        """Невозможно создать две заметки с одинаковым slug."""
        self.notes = Note.objects.create(
            title='Заголовок',
            text='Текст',
            slug='slug',
            author=self.author)
        url = reverse('notes:add')
        notes_count = Note.objects.count()
        self.form_data['slug'] = self.notes.slug
        response = self.author_client.post(url, data=self.form_data)
        notes_count_after_add = Note.objects.count()
        self.assertFormError(response,
                             'form',
                             'slug',
                             errors=(
                                 self.notes.slug + WARNING
                                 )
                             )
        self.assertEqual(notes_count, notes_count_after_add)


class TestNoteEditAndDelete(TestCase):
    """Тестирование логики редактирования и удаления заметок"""

    NEW_TITLE = 'Новый заголовок'
    NEW_TEXT = 'Новый текст заметки'
    NEW_SLUG = 'new_slug'

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Автор')
        cls.reader = User.objects.create(username='Пользователь')
        cls.note = Note.objects.create(
            title=TITLE,
            text=TEXT,
            slug=SLUG,
            author=cls.author
        )
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)
        cls.form_data = {
            'title': cls.NEW_TITLE,
            'text': cls.NEW_TEXT,
            'slug': cls.NEW_SLUG
        }

    def test_author_can_delete_note(self):
        """Удаление заметки автором"""
        url = reverse('notes:delete', args={'slug': self.note.slug})
        notes_count = Note.objects.count()
        response = self.author_client.delete(url, data=self.form_data)
        self.assertRedirects(response, reverse('notes:success'))
        notes_count_after_delete = Note.objects.count()
        self.assertEqual(notes_count - 1, notes_count_after_delete)

    def test_author_can_edit_note(self):
        """Редактирование заметки автором"""
        url = reverse('notes:edit', args={'slug': self.note.slug})
        url_success = reverse('notes:success')
        response = self.author_client.post(url, data=self.form_data)
        self.assertRedirects(response, url_success)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, self.NEW_TITLE)
        self.assertEqual(self.note.text, self.NEW_TEXT)
        self.assertEqual(self.note.slug, self.NEW_SLUG)
        self.assertEqual(self.note.author, self.author)

    def test_reader_cant_delete_note(self):
        """Удаление заметки другим пользователем"""
        delete_note_url = reverse(
            'notes:delete',
            args={'slug': self.note.slug}
        )
        notes_count = Note.objects.count()
        response = self.reader_client.delete(delete_note_url, self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        notes_count_after_delete = Note.objects.count()
        self.assertEqual(notes_count, notes_count_after_delete)

    def test_user_cant_edit_strangers_note(self):
        """Редактирование заметки другим пользователем"""
        edit_note_url = reverse('notes:edit', args={'slug': self.note.slug})
        response = self.reader_client.post(edit_note_url, data=self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.note.refresh_from_db()
        self.assertEqual(self.note.text, TEXT)
