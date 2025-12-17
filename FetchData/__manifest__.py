# -*- coding: utf-8 -*-
{
    'name': "Fetch Data",
    'summary': "fetch data from Mysql db",
    'description': "fetch data from another db",
    'author': "Vikash Tiwari",
    'category': 'Fetch Data',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'custom_project_management'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/fetch_all_tables_data.xml',
    ],
    'license': 'OPL-1',

}
