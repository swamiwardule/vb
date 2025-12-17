{
    'name': 'Custom Branding',
    'version': '16.0.1.1.0',
    'category': 'Tools',
    'depends': ['web'],
    'data': ['static/src/xml/custom_template.xml',
             'views/custom_favicon.xml',],

    # 'assets': {
    #     'web.assets_backend': [
    #         'custom_branding/static/src/js/custom_title.js',
    #         'custom_branding/static/src/js/custom_content.js',
    #     ],
    # },
    'installable': True,
    'auto_install': False,
}
