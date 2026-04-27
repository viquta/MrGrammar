from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_healthz_returns_ok_or_degraded_payload(self):
        response = self.client.get('/healthz/')

        self.assertIn(response.status_code, (200, 503))
        body = response.json()

        self.assertIn('status', body)
        self.assertIn(body['status'], ('ok', 'degraded'))
        self.assertIn('checks', body)
        self.assertIn('database', body['checks'])
        self.assertIn('cache', body['checks'])
