__author__ = 'Luis Villazon Esteban'

import unittest
from jinja2 import Template
from jinja2 import Environment, PackageLoader

class NinjaTest(unittest.TestCase):

    def test_resolve_simple_template(self):
        user_data = "{{queue}} is {{site}}"
        params_to_create = {
            'queue': 'good',
            'site': 'bad'
        }
        template = Template(user_data)
        user_data = template.render(params_to_create)
        self.assertEqual(user_data, "good is bad")

    def test_resolve_multiple_dictionary(self):
        user_data = "{{queue}} is {{params.site}}"
        params_to_create = {
            'queue': 'good',
            'params': {'site': 'bad'}
        }
        template = Template(user_data)
        user_data = template.render(params_to_create)
        self.assertEqual(user_data, "good is bad")

    def test_resolve_with_condition(self):
        user_data = "{% if GOOD %}good{% elif BEST %}best{% else %}bad{% endif %}"
        params_to_create = {
            'GOOD': 'GOOD',
            'BEST': None,
            'BAD' : None
        }
        template = Template(user_data)
        exit = template.render(params_to_create)
        self.assertEqual(exit, "good")

        params_to_create = {
            'GOOD': None,
            'BEST': 'BEST',
            'BAD' : None
        }
        template = Template(user_data)
        exit = template.render(params_to_create)
        self.assertEqual(exit, "best")

        params_to_create = {
            'GOOD': None,
            'BEST': None,
            'BAD' : 'BAD'
        }
        template = Template(user_data)
        exit = template.render(params_to_create)
        self.assertEqual(exit, "bad")

    def test_from_file(self):
        env = Environment(loader=PackageLoader('vcycle', 'contextualization'))
        template = env.get_template('test')
        exit = template.render()
        print exit

if __name__ == '__main__':
    unittest.main()

