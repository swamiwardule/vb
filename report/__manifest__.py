# -*- coding: utf-8 -*-
{
    'name': "Project Report",
    'summary': "",
    'description': "",
    'author': "",
    'category': '',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','custom_project_management'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/project_report_view.xml',
        'views/project_report_template.xml',
        'views/project_report_action.xml',
        # 'data/synch_data_cron.xml',
        #'security/ir.model.access.csv',
        # 'security/security_groups.xml',
        
    ],
    'license': 'OPL-1',

}
