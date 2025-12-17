# -*- coding: utf-8 -*-
{
    'name': "Project Informations",
    'summary': "",
    'description': "",
    'author': "Falguni Tank",
    'category': 'Building Flats',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        'data/res_group_inherit.xml',
        'data/ir_cron_data.xml',
        'data/status_confirmation_mail.xml',
        # 'data/synch_data_cron.xml',
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        # 'security/security_groups.xml',
        'views/project_info_view.xml',
        'views/configurations_view.xml',
        'views/project_activity_status_manully.xml',
        'views/project_menu.xml',
        'views/print_nc_report.xml',
        'views/notification.xml',
        'views/res_users_views.xml',
        'views/master_table_views.xml',
        'views/material_inspection_view.xml',
        'views/report_manual_flag.xml',
        'views/project_menu.xml',

        # 'views/fetch_all_tables_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_project_management/static/src/css/kanban_view.css',
            'custom_project_management/static/src/js/set_title.js',
        ],
    },
    'license': 'OPL-1',

}
