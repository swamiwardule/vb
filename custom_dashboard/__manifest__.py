# -*- coding: utf-8 -*-
{
    'name': "Open Dashboard",
    'version': '16.0.1.0.1',
    'author': 'Vikash Tiwari',
    'company': 'ITeSolution Technologies Pvt. Ltd.',
    'maintainer': 'ITeSolution Technologies Pvt. Ltd.',
    'website': "http://www.itesolution.co.in",
    'depends': ['base', 'custom_project_management'],
    'external_dependencies': {
        'python': ['pandas'],
    },
    'data': ['data/access_group.xml',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_dashboard/static/src/css/custom_dashboard.css',
            'custom_dashboard/static/src/js/custom_dashboard.js',
            'custom_dashboard/static/src/xml/custom_dashboard.xml',
        ],
    },
    'images': ["static/description/dashboard_icon.png"],
    'license': "AGPL-3",
    'installable': True,
    'application': True,
}
