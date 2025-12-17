{
    'name': 'Report Wizard',
    'version': '16.0',
    'category': 'Project',
    'summary': 'Wizard to report of project',
    'depends': ['base', 'custom_project_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/template_view.xml',
        'views/template_final.xml',
        'views/custom_print_format.xml',
        # 'views/hide_button.xml',

    ],
#     'assets': {
#     'web.assets_backend': [
#         'custom_report/static/src/css/custom.css',
#         # 'custom_report/static/src/js/custom.js',

#     ],
# },
    'installable': True,
    'application': True,
    'auto_install': False,
}
