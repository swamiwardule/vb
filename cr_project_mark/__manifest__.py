# -*- coding: utf-8 -*-
{
    'name': "Project Mark Count",
    'summary': "",
    'description': "",
    'author': "",
    'category': 'Building Flats',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'custom_project_management'],

    # always loaded
    'data': [
        'data/ir_cron_data.xml',
        'views/config.xml',
    ],
    'license': 'OPL-1',

}
