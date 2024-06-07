from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Turnus
import os


class TurnusUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('uploadFile')
        self.test_file_path = os.path.join(
            os.path.dirname(__file__), 'test_data.xlsx')
        self.test_file = SimpleUploadedFile(
            name='test_data.xlsx',
            content=open(self.test_file_path, 'rb').read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_turnus_upload_and_process(self):
        response = self.client.post(self.url, {'uploadedFile': self.test_file})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Turnus.objects.exists())
        turnus = Turnus.objects.last()
        self.assertIsNotNone(turnus.uploadedFile)
        self.assertTrue(os.path.exists(turnus.uploadedFile.path))
