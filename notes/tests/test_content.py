from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from http import HTTPStatus

from notes.forms import NoteForm
from notes.models import Note

User = get_user_model()


class TestContent(TestCase):
    """Тестирование контента"""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Автор Заметки')
        cls.reader = User.objects.create(username='Левый персонаж')
        cls.note = Note.objects.create(
            title='Заголовок',
            text='Текст',
            author=cls.author
        )
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)

    def test_notes_list_access(self):
        """Тестирование доступа к заметкам на странице

        Отдельная заметка передаётся на страницу со списком заметок в
        списке object_list, в словаре context;

        В список заметок одного пользователя не попадают
        заметки другого пользователя;
        """
        url = reverse('notes:list')
        client = self.author_client or self.reader_client
        response = client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        notes = response.context['object_list']
        if self.author_client:
            self.assertIn(self.note, notes)
        elif self.reader_client:
            self.assertNotIn(self.note, notes)

    def test_create_and_add_forms(self):
        """На страницы создания и редактирования заметки передаются формы."""
        urls = (
            ('notes:add', None),
            ('notes:edit', (self.note.slug,))
        )
        for name, args in urls:
            with self.subTest(name=name):
                url = reverse(name, args=args)
                response = self.author_client.get(url)
                self.assertIsInstance(response.context['form'], NoteForm)
