import os

from locust import HttpUser, between, task


class MrGrammarUser(HttpUser):
    """Baseline user profile for production smoke and concurrency tests."""

    wait_time = between(1, 3)
    token = None

    def on_start(self):
        username = os.environ.get('LOCUST_USERNAME')
        password = os.environ.get('LOCUST_PASSWORD')

        if not username or not password:
            return

        response = self.client.post(
            '/api/auth/login/',
            json={'username': username, 'password': password},
            name='/api/auth/login/',
        )

        if response.status_code == 200:
            self.token = response.json().get('access')

    @task(5)
    def healthz(self):
        self.client.get('/healthz/', name='/healthz/')

    @task(2)
    def load_root(self):
        self.client.get('/', name='/')

    @task(3)
    def list_submissions(self):
        if not self.token:
            return

        self.client.get(
            '/api/submissions/',
            headers={'Authorization': f'Bearer {self.token}'},
            name='/api/submissions/',
        )

    @task(2)
    def student_progress(self):
        if not self.token:
            return

        student_id = os.environ.get('LOCUST_STUDENT_ID')
        if not student_id:
            return

        self.client.get(
            f'/api/analytics/student/{student_id}/progress/',
            headers={'Authorization': f'Bearer {self.token}'},
            name='/api/analytics/student/{id}/progress/',
        )
