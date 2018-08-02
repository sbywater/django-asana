Testing Your Code
=================

Asana does not provide a testing sandbox API. When testing the integration of your application with Asana, you will likely want to mock any connections to Asana that would write data to avoid creating a lot of junk data in Asana.

Some strategies for testing with django-asana are as follows:

  - Override the ASANA_ACCESS_TOKEN setting so that if your tests do reach out to Asana they will get an authentication error instead of writing bad data. This would be unnecessary if you follow the other steps, but by adding it to your TestCase, any new tests that do not mock your connections to Asana will fail loudly. If you want to test a read from Asana, you would not want to override your credentials.

  - Mock the connection itself. django-asana provides some mock responses you can test with.

  - When you need multiple mocks returned for database insertion, you will want them all to have unique ids to avoid integrity errors.


.. code:: python

    from unittest.mock import MagicMock, patch

    from django.test import TestCase, override_settings
    from unittest.mock import patch

    def counter():
    count = 1
    while True:
        yield count
        count += 1


    COUNTER = counter()


    def get_task(**kwargs):
        if 'assignee' in kwargs:
            kwargs['assignee'] = {'id': kwargs['assignee']}
        if 'parent' in kwargs:
            kwargs['parent'] = {'id': kwargs['parent']}
        return task(**kwargs)


    def new_task(**kwargs):
        """Returns a mock Asana response for a task create."""
        task_ = get_task(**kwargs)
        task_['id'] = next(COUNTER)
        return task_


    def update_task(*args):
        """Returns a mock Asana response for an update.

        update gets passed a tuple: (id, dict)
        """
        kwargs = {key: value for key, value in args[1].items()}
        task_ = get_task(**kwargs)
        task_['id'] = args[0]
        return task_


    @override_settings(ASANA_ACCESS_TOKEN='foo')  # Assures your credentials are not real
    class TestTask(TestCase):

    @patch('djasana.models.client_connect')
    def test_update_date_tasks(self, mock_connect):
        """Demonstrates how to mock for testing purposes."""
        mock_client = mock_connect.return_value
        mock_client.tasks.find_all.return_value = [task()]
        mock_client.tasks.create.side_effect = new_task
        mock_client.tasks.update.side_effect = update_task
        mock_client.tasks.set_parent.side_effect = new_task
        # Do something with those mocks
