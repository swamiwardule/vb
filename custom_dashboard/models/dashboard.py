from odoo import models, fields, api, _
import logging
from odoo import http, _
_logger = logging.getLogger(__name__)


class ProjectInfo(models.Model):
    _inherit = "project.info"

    @api.model
    def run_project_count_scheduler(self):
        records = self.search([])  # or use a domain to limit projects
        records.get_all_project_nc_count()

    @api.model
    def get_all_project_info_count(self):
        try:
            all_project_info = self.env['project.info'].search([])
            total_project = len(all_project_info)
        except Exception as e:
            total_project = 0
            error_message = _(
                "An error occurred while retrieving project info count: %s") % str(e)
            # Log the error or handle it appropriately
            _logger.error(error_message)
        return {'total_project': total_project}

    @api.model
    def get_project_names(self):
        project_names = self.env['project.info'].search_read([], ['name'])
        return project_names

    def tower_name_list(self, project_id=False, tower=False):
        print(tower, 'tower---project_name_list\n\n\n-project id -----', project_id)
        # if tower:
        #     projects = self.search([('project_info_tower_line', '=', project_id)])
        # else:
        if tower:
            towers = self.env['project.tower'].search([('id', '=', tower)])
        else:
            towers = self.search([])  # Retrieve all project records
        tower_list = []
        for tower in towers:
            tower_list.append(tower.name)
        return tower_list

    def project_name_list(self, project_id=False, tower=False):
        # if tower:
        #     projects = self.search([('project_info_tower_line', '=', project_id)])
        # else:
        if project_id:
            projects = self.search([('id', '=', project_id)])
        else:
            projects = self.search([])
        project_list = []
        for project in projects:
            project_list.append(project.name)
        return project_list

    @api.model
    def get_all_project_nc_count(self):
        _logger.info(
            "==============get_all_project_nc_count is called===========")
        all_projects = self.env['manually.set.flag'].search(
            [('status', 'in', ['open', 'submit'])]
        )
        total_nc_count = 0
        total_yellow_flag_count = 0
        total_red_flag_count = 0
        total_orange_flag_count = 0
        total_green_flag_count = 0
        if all_projects:
            total_nc_count = 0
            total_yellow_flag_count = 0
            total_red_flag_count = 0
            total_orange_flag_count = 0
            total_green_flag_count = 0
        for matched_project in all_projects:
            total_nc_count += int(matched_project.cre_nc or 0)
            total_yellow_flag_count += int(matched_project.cre_yellow or 0)
            total_orange_flag_count += int(matched_project.cre_orange or 0)
            total_red_flag_count += int(matched_project.cre_red or 0)
            total_green_flag_count += int(matched_project.cre_Green or 0)
        return {
            'total_nc_count': total_nc_count,
            'total_yellow_flag_count': total_yellow_flag_count,
            'total_orange_flag_count': total_orange_flag_count,
            'total_red_flag_count': total_red_flag_count,
            'total_green_flag_count': total_green_flag_count,
        }

    @api.model
    def get_project_wise_details_new(self, selected_value, project_detailsValue):
        print('==============project_detailsValue======\n\n\n\n',
              project_detailsValue)
        project_details = []

        if selected_value:
            # Search for projects with a domain that includes project_detailsValue
            projects = self.search([
                ('id', '=', int(selected_value)),
                # ('project_details_line.name', '=', project_detailsValue)
            ])

            if projects:
                for project in projects:
                    nc_count = 0
                    yellow_flag_count = 0
                    orange_flag_count = 0
                    red_flag_count = 0
                    green_flag_count = 0

                    matched_projects = self.env['manually.set.flag'].search([
                        ('project_info_id', '=', project.id),
                        ('status', 'in', ['open', 'submit'])
                    ])
                    # for matched_project in matched_projects:
                    #     nc_count += int(matched_project.cre_nc)
                    #     yellow_flag_count += int(matched_project.cre_yellow)
                    #     orange_flag_count += int(matched_project.cre_orange)
                    #     red_flag_count += int(matched_project.cre_red)
                    #     green_flag_count += int(matched_project.cre_Green)
                    for matched_project in matched_projects:
                        if matched_project.flag_category == 'Nc':
                            nc_count += 1
                        elif matched_project.flag_category == 'Yellow Flag':
                            yellow_flag_count += 1
                        elif matched_project.flag_category == 'Orange Flag':
                            orange_flag_count += 1
                        elif matched_project.flag_category == 'Red Flag':
                            red_flag_count += 1
                        elif matched_project.flag_category == 'Green Flag':
                            green_flag_count += 1

                vals = {
                    'nc_count': nc_count,
                    'yellow_flag_count': yellow_flag_count,
                    'orange_flag_count': orange_flag_count,
                    'red_flag_count': red_flag_count,
                    'green_flag_count': green_flag_count
                }

                for r in ['nc_count', 'yellow_flag_count', 'orange_flag_count', 'red_flag_count', 'green_flag_count']:
                    project_details.append({'label': r, 'value': vals[r]})
        print('============project_details========', project_details)
        return project_details

    @api.model
    def get_project_nc_count(self, projectValue, towerValue):
        projects = self.search([('id', '=', int(projectValue))])
        project_details = []
        if projects:
            for project in projects:
                nc_count = 0
                yellow_flag_count = 0
                orange_flag_count = 0
                red_flag_count = 0
                green_flag_count = 0

                matched_projects = self.env['manually.set.flag'].search(
                    [('project_info_id', '=', project.id), ('status', 'in', ['open', 'submit'])]
                )

                for matched_project in matched_projects:
                    nc_count += int(matched_project.cre_nc or 0)
                    yellow_flag_count += int(matched_project.cre_yellow or 0)
                    orange_flag_count += int(matched_project.cre_orange or 0)
                    red_flag_count += int(matched_project.cre_red or 0)
                    green_flag_count += int(matched_project.cre_Green or 0)

                project_details.append({
                    'name': project.name,
                    'nc_count': nc_count,
                    'yellow_flag_count': yellow_flag_count,
                    'orange_flag_count': orange_flag_count,
                    'red_flag_count': red_flag_count,
                    'green_flag_count': green_flag_count
                })

                count_list_nc = {r['name']: r['nc_count']
                                 for r in project_details}
                count_list_yc = {r['name']: r['yellow_flag_count']
                                 for r in project_details}
                count_list_oc = {r['name']: r['orange_flag_count']
                                 for r in project_details}
                count_list_rc = {r['name']: r['red_flag_count']
                                 for r in project_details}
                count_list_gc = {r['name']: r['green_flag_count']
                                 for r in project_details}

                graph_result = [
                    {'l_month': 'NC', 'leave': count_list_nc},
                    {'l_month': 'YC', 'leave': count_list_yc},
                    {'l_month': 'OC', 'leave': count_list_oc},
                    {'l_month': 'RC', 'leave': count_list_rc},
                    {'l_month': 'GC', 'leave': count_list_gc}
                ]
                project_list = self.project_name_list(projectValue, towerValue)

            return graph_result, project_list
        else:
            return [], []

        # if projects:
        #     nc_count = 0
        #     yellow_flag_count = 0
        #     orange_flag_count = 0
        #     red_flag_count = 0
        #     green_flag_count = 0
        #
        #     for project in projects:
        #         matched_projects = self.env['manually.set.flag'].search(
        #             [('project_info_id', '=', project.id), ('status', '=', 'open')])
        #         for matched_project in matched_projects:
        #             nc_count += int(matched_project.cre_nc)
        #             yellow_flag_count += int(matched_project.cre_yellow)
        #             orange_flag_count += int(matched_project.cre_orange)
        #             red_flag_count += int(matched_project.cre_red)
        #             green_flag_count += int(matched_project.cre_Green)
        #     vals = {
        #         'nc_count': nc_count,
        #         'yellow_flag_count': yellow_flag_count,
        #         'orange_flag_count': orange_flag_count,
        #         'red_flag_count': red_flag_count,
        #         'green_flag_count': green_flag_count
        #     }
        #     project_list = self.project_name_list(projectValue, towerValue)
        #     for r in ['nc_count', 'yellow_flag_count', 'orange_flag_count', 'red_flag_count', 'green_flag_count']:
        #         project_details.append({'label': r, 'value': vals[r]})
        #     return project_details, project_list
        # else:
        #     return [], []

    # @api.model
    # def get_project_nc_count(self, projectValue, towerValue):
    #     # projects = self.search([])
    #     projects = self.search([('id', '=', int(projectValue))])
    #     project_details = []
    #     for project in projects:
    #         project_details.append({'name': project.name, 'nc_count': project.nc_count,
    #                                 'yellow_flag_count': project.yellow_flag_count,
    #                                 'orange_flag_count': project.orange_flag_count,
    #                                 'red_flag_count': project.red_flag_count,
    #                                 'green_flag_count': project.green_flag_count})
    #     project_list = self.project_name_list(projectValue, towerValue)
    #     count_list_nc = {}
    #     count_list_yc = {}
    #     count_list_oc = {}
    #     count_list_rc = {}
    #     count_list_gc = {}
    #     for r in project_details:
    #         count_list_nc[r['name']] = r['nc_count']
    #         count_list_yc[r['name']] = r['yellow_flag_count']
    #         count_list_oc[r['name']] = r['orange_flag_count']
    #         count_list_rc[r['name']] = r['red_flag_count']
    #         count_list_gc[r['name']] = r['green_flag_count']
    #         # b= r['nc_count']
    #     graph_result = [{'l_month': 'NC', 'leave': count_list_nc},
    #         {'l_month': 'YC', 'leave': count_list_yc},
    #         {'l_month': 'OC', 'leave': count_list_oc},
    #         {'l_month': 'RC', 'leave': count_list_rc},
    #         {'l_month': 'GC', 'leave': count_list_gc}]
    #     return graph_result, project_list

    # @api.model
    # def get_c_m_a_data(self, project_id, tower):
    #     if tower:
    #         projects = self.env['project.activity.type'].search([('tower_id', '=', int(tower))])
    #         project_list = self.tower_name_list(project_id, tower)
    #     else:
    #         if project_id:
    #             projects = self.env['project.activity.type'].search([('project_id', '=', int(project_id))])
    #             project_list = self.project_name_list(project_id, tower)
    #     graph_result = []
    #     name = (projects[0].tower_id.name if tower else projects[0].project_id.name) if projects else ''
    #     for activity_type in ['Checker', 'Maker', 'Approver']:
    #         draft_count = 0
    #         submit_count = 0
    #         checked_count = 0
    #         approved_count = 0
    #         for activity in projects:
    #             if activity.status == 'draft':
    #                 draft_count += 1
    #             elif activity.status == 'submit':
    #                 submit_count += 1
    #             elif activity.status == 'checked':
    #                 checked_count += 1
    #             elif activity.status == 'approve':
    #                 approved_count += 1
    #         activity_counts = {}
    #         if activity_type == 'Maker':
    #             activity_counts[name] = draft_count
    #         elif activity_type == 'Checker':
    #             activity_counts[name] = submit_count
    #         elif activity_type == 'Approver':
    #             activity_counts[name] = checked_count
    #         graph_result.append({'l_month': activity_type, 'leave': activity_counts})
    #     print('-----111graph_result------', graph_result)
    #     return graph_result, project_list

    @api.model
    def get_c_m_a_data(self, project_id, tower, extra_arg=None):
        domain = []
        if tower:
            domain = [('tower_id', '=', int(tower))]
            project_list = self.tower_name_list(project_id, tower)
        elif project_id:
            domain = [('project_id', '=', int(project_id))]
            project_list = self.project_name_list(project_id, tower)

        projects = self.env['project.activity.type'].search(domain)

        # Initialize counts
        counts = {
            'Checker': 0,
            'Maker': 0,
            'Approver': 0
        }

        name = (
            projects[0].tower_id.name if tower else projects[0].project_id.name) if projects else ''

        for activity in projects:
            if activity.status == 'checked' or activity.status == 'approve':
                counts['Checker'] += 1
            if activity.status in ['submit', 'checked', 'approve']:
                counts['Maker'] += 1
            if activity.status == 'approve':
                counts['Approver'] += 1

        graph_result = []
        for activity_type in ['Maker', 'Checker', 'Approver']:
            activity_counts = {name: counts[activity_type]}
            graph_result.append(
                {'l_month': activity_type, 'leave': activity_counts})

        print('-----111graph_result------', graph_result)
        return graph_result, project_list

    # @api.model
    # def get_c_m_a_data(self, project_id, tower):
    #     domain = []
    #     if tower:
    #         domain = [('tower_id', '=', int(tower))]
    #         # domain = [('tower_id', '=', int(tower)),('project_details_line.name', '=', project_detailsValue), ('project_details_line.tower_id', '=', int(tower))]
    #         project_list = self.tower_name_list(project_id, tower)
    #     elif project_id:
    #         domain = [('project_id', '=', int(project_id))]
    #         project_list = self.project_name_list(project_id, tower)

    #     projects = self.env['project.activity.type'].search(domain)

    #     # Initialize counts
    #     counts = {
    #         'Checker': 0,
    #         'Maker': 0,
    #         'Approver': 0
    #     }

    #     name = (
    #         projects[0].tower_id.name if tower else projects[0].project_id.name) if projects else ''

    #     for activity in projects:
    #         if activity.status == 'checked' or activity.status == 'approve':
    #             counts['Checker'] += 1
    #         if activity.status == 'submit' or activity.status == 'checked' or activity.status == 'approve':
    #             counts['Maker'] += 1
    #         if activity.status == 'approve':
    #             counts['Approver'] += 1

    #     graph_result = []
    #     for activity_type in ['Maker', 'Checker', 'Approver']:
    #         activity_counts = {name: counts[activity_type]}
    #         graph_result.append(
    #             {'l_month': activity_type, 'leave': activity_counts})

    #     print('-----111graph_result------', graph_result)
    #     return graph_result, project_list

    @api.model
    def get_pending_c_m_a_data(self, project_id, tower):
        domain = []
        if tower:
            domain = [('tower_id', '=', int(tower))]
            project_list = self.tower_name_list(project_id, tower)
        elif project_id:
            domain = [('project_id', '=', int(project_id))]
            project_list = self.project_name_list(project_id, tower)

        projects = self.env['project.activity.type'].search(domain)

        # Initialize counts
        counts = {
            'Maker': 0,
            'Checker': 0,
            'Approver': 0
        }

        name = (
            projects[0].tower_id.name if tower else projects[0].project_id.name) if projects else ''

        for activity in projects:
            if activity.status == 'draft':
                counts['Maker'] += 1
            elif activity.status == 'submit':
                counts['Checker'] += 1
            elif activity.status == 'checked':
                counts['Approver'] += 1

        graph_result = []
        for activity_type in ['Maker', 'Checker', 'Approver']:
            activity_counts = {name: counts[activity_type]}
            graph_result.append(
                {'l_month': activity_type, 'leave': activity_counts})

        print('-----2222graph_result------', graph_result)
        return graph_result, project_list

    # @api.model
    # def get_pending_c_m_a_data(self, project_id, tower):
    #     if tower:
    #         projects = self.env['project.activity.type'].search([('tower_id', '=', int(tower))])
    #         project_list = self.tower_name_list(project_id, tower)
    #     else:
    #         if project_id:
    #             projects = self.env['project.activity.type'].search([('project_id', '=', int(project_id))])
    #             project_list = self.project_name_list(project_id, tower)
    #     graph_result = []
    #     name = (projects[0].tower_id.name if tower else projects[0].project_id.name) if projects else ''
    #     for activity_type in ['Checker', 'Maker', 'Approver']:
    #         draft_count = 0
    #         submit_count = 0
    #         checked_count = 0
    #         approved_count = 0
    #         for activity in projects:
    #             if activity.status == 'draft':
    #                 draft_count += 1
    #             elif activity.status == 'submit':
    #                 submit_count += 1
    #             elif activity.status == 'checked':
    #                 checked_count += 1
    #             elif activity.status == 'approve':
    #                 approved_count += 1
    #         activity_counts = {}
    #         if activity_type == 'Maker':
    #             activity_counts[name] = draft_count
    #         elif activity_type == 'Checker':
    #             activity_counts[name] = submit_count
    #         elif activity_type == 'Approver':
    #             activity_counts[name] = checked_count
    #         graph_result.append({'l_month': activity_type, 'leave': activity_counts})
    #     print('-----2222graph_result------', graph_result)
    #     return graph_result, project_list


class ProjectTower(models.Model):
    _inherit = "project.tower"

    @api.model
    def get_all_project_towers(self):
        try:
            all_project_tower = self.env['project.tower'].search([])
            total_tower = len(all_project_tower)
        except Exception as e:
            total_tower = 0
            error_message = _(
                "An error occurred while retrieving project tower count: %s") % str(e)
            # Log the error or handle it appropriately
            _logger.error(error_message)
        return {
            'total_tower': total_tower
        }

    @api.model
    def get_tower_names(self, projectValue, project_detailsValue):
        print('=========projectValue=========project_detailsValue---',
              projectValue, project_detailsValue)

        if projectValue or project_detailsValue:
            # Construct domain for project.info
            project_id = int(projectValue)
            domain = [('id', '=', project_id)]

            # Fetch project tower names and related tower ids
            project_ids = self.env['project.info'].search(domain, limit=1)

            tower_ids = []
            for rec in project_ids:
                for r in rec.project_details_line:
                    if r.name == project_detailsValue:
                        tower_ids.append(r.tower_id.ids)

            # Fetch tower names based on tower_ids
            print('=====\n\n\n====tower_ids===', tower_ids)
            if tower_ids:
                tower_names = self.env['project.tower'].search_read(
                    [('id', 'in', tower_ids[0])], ['name'])
            else:
                tower_names = []

            print(domain, '========tower_names======', tower_names)
            return tower_names

        return []

    # @api.model
    # def get_tower_names(self, projectValue, project_detailsValue):
    #     domain = []
    #     print('=========123456789sdfgh==projectValue=========project_detailsValue---', projectValue, project_detailsValue)
    #     if projectValue or project_detailsValue:
    #         domain = [('project_id', '=', int(projectValue))]
    #         # domain = [('project_id', '=', int(projectValue))]
    #         project_tower_names = self.env['project.info'].search(domain)
    #         tower_ids = []
    #         for rec in project_tower_names:
    #             if rec.project_details_line.name == project_detailsValue:
    #                 tower_ids.append(rec.project_details_line.tower_id.id)
    #         tower_names = self.env['project.tower'].search_read(domain, ['name'])
    #         print(domain, '========tower_names======', tower_names)
    #         return tower_names
    #     else:
    #         return domain

    @api.model
    def get_tower_wise_details(self, selected_value, projectValue, project_detailsValue):

        project_details = []
        # projects = self.env['project.info'].search([
        #     ('id', '=', int(selected_value)),
        #     ('project_details_line.tower_id', '=', project_detailsValue)
        # ])
        if selected_value:
            towers = self.search([('id', '=', selected_value)])
            for tower in towers:
                nc_count = 0
                yellow_flag_count = 0
                orange_flag_count = 0
                red_flag_count = 0
                green_flag_count = 0

                matched_projects = self.env['manually.set.flag'].search(
                    [('project_tower_id', '=', tower.id), ('status', 'in', ['open', 'submit'])
])
                # for matched_project in matched_projects:
                #     nc_count += int(matched_project.cre_nc)
                #     yellow_flag_count += int(matched_project.cre_yellow)
                #     orange_flag_count += int(matched_project.cre_orange)
                #     red_flag_count += int(matched_project.cre_red)
                #     green_flag_count += int(matched_project.cre_Green)
                for matched_project in matched_projects:
                        if matched_project.flag_category == 'Nc':
                            nc_count += 1
                        elif matched_project.flag_category == 'Yellow Flag':
                            yellow_flag_count += 1
                        elif matched_project.flag_category == 'Orange Flag':
                            orange_flag_count += 1
                        elif matched_project.flag_category == 'Red Flag':
                            red_flag_count += 1
                        elif matched_project.flag_category == 'Green Flag':
                            green_flag_count += 1

                vals = {
                    'nc_count': nc_count,
                    'yellow_flag_count': yellow_flag_count,
                    'orange_flag_count': orange_flag_count,
                    'red_flag_count': red_flag_count,
                    'green_flag_count': green_flag_count
                }

            for r in ['nc_count', 'yellow_flag_count', 'orange_flag_count', 'red_flag_count', 'green_flag_count']:
                project_details.append({'label': r, 'value': vals[r]})

        # print('---------tower_details\n\n\n\n\n\n\n\n\n------', project_details)
        return project_details

    def tower_name_list(self, project_id=False, tower=False):
        # if tower:
        #     projects = self.search([('project_info_tower_line', '=', project_id)])
        # else:
        if tower:
            towers = self.search([('id', '=', tower)])
        else:
            towers = self.search([])  # Retrieve all project records
        tower_list = []
        for tower in towers:
            tower_list.append(tower.name)
        return tower_list

    @api.model
    def get_tower_counts(self, projectValue, towerValue):
        towers = self.search([('id', '=', towerValue)]
                             ) if towerValue else self.search([])

        # domain = [('tower_id', '=', int(towerValue)), ('project_details_line.name', '=', project_detailsValue),
        #           ('project_details_line.tower_id', '=', int(towerValue))]
        # project_ids = self.env['project.info'].search(domain)
        if towerValue:
            towers = self.search([('id', '=', towerValue)])
        towers_details = []
        if towers:
            for tower in towers:
                nc_count = 0
                yellow_flag_count = 0
                orange_flag_count = 0
                red_flag_count = 0
                green_flag_count = 0

                matched_projects = self.env['manually.set.flag'].search(
                    [('project_tower_id', '=', tower.id), ('status', 'in', ['open', 'submit'])])

                for matched_project in matched_projects:
                    nc_count += int(matched_project.cre_nc or 0)
                    yellow_flag_count += int(matched_project.cre_yellow or 0)
                    orange_flag_count += int(matched_project.cre_orange or 0)
                    red_flag_count += int(matched_project.cre_red or 0)
                    green_flag_count += int(matched_project.cre_Green or 0)

                towers_details.append({
                    'name': tower.name,
                    'nc_count': nc_count,
                    'yellow_flag_count': yellow_flag_count,
                    'orange_flag_count': orange_flag_count,
                    'red_flag_count': red_flag_count,
                    'green_flag_count': green_flag_count
                })

            count_list_nc = {r['name']: r['nc_count'] for r in towers_details}
            count_list_yc = {r['name']: r['yellow_flag_count']
                             for r in towers_details}
            count_list_oc = {r['name']: r['orange_flag_count']
                             for r in towers_details}
            count_list_rc = {r['name']: r['red_flag_count']
                             for r in towers_details}
            count_list_gc = {r['name']: r['green_flag_count']
                             for r in towers_details}

            graph_result = [
                {'l_month': 'NC', 'leave': count_list_nc},
                {'l_month': 'YC', 'leave': count_list_yc},
                {'l_month': 'OC', 'leave': count_list_oc},
                {'l_month': 'RC', 'leave': count_list_rc},
                {'l_month': 'GC', 'leave': count_list_gc}
            ]
            tower_list = self.tower_name_list(projectValue, towerValue)
            return graph_result, tower_list
        else:
            return [], []


class ProjectFloors(models.Model):
    _inherit = "project.floors"

    @api.model
    def get_floors_names(self):
        floors_names = self.env['project.floors'].search_read([], ['name'])
        return floors_names

    @api.model
    def get_all_project_floors(self):
        try:
            all_project_floors = self.env['project.floors'].search([])
            total_floors = len(all_project_floors)
        except Exception as e:
            total_floors = 0
            error_message = _(
                "An error occurred while retrieving project floors count: %s") % str(e)
            # Log the error or handle it appropriately
            _logger.error(error_message)
        return {
            'total_floors': total_floors
        }

    # @api.model
    # def get_floor_wise_details(self):
    #     floor_details = []
    #     all_floors = self.search([])
    #     for tower in all_floors:
    #         matched_flags = self.env['manually.set.flag'].search_count([('project_floor_id', '=', tower.id),
    #                                                                     ('status', '=', 'open')])
    #         floor_details.append({'label': tower.name, 'value': matched_flags})
    #     return floor_details

    @api.model
    def get_floor_wise_details(self, selected_value):
        project_details = []
        projects = self.search([('id', '=', selected_value)])
        if projects:
            for project in projects:
                nc_count = 0
                yellow_flag_count = 0
                orange_flag_count = 0
                red_flag_count = 0
                green_flag_count = 0

                matched_projects = self.env['manually.set.flag'].search(
                    [('project_floor_id', '=', project.id), ('status', 'in', ['open', 'submit'])
])
                # for matched_project in matched_projects:
                #     nc_count += int(matched_project.cre_nc)
                #     yellow_flag_count += int(matched_project.cre_yellow)
                #     orange_flag_count += int(matched_project.cre_orange)
                #     red_flag_count += int(matched_project.cre_red)
                #     green_flag_count += int(matched_project.cre_Green)
                for matched_project in matched_projects:
                        if matched_project.flag_category == 'Nc':
                            nc_count += 1
                        elif matched_project.flag_category == 'Yellow Flag':
                            yellow_flag_count += 1
                        elif matched_project.flag_category == 'Orange Flag':
                            orange_flag_count += 1
                        elif matched_project.flag_category == 'Red Flag':
                            red_flag_count += 1
                        elif matched_project.flag_category == 'Green Flag':
                            green_flag_count += 1

            vals = {
                'nc_count': nc_count,
                'yellow_flag_count': yellow_flag_count,
                'orange_flag_count': orange_flag_count,
                'red_flag_count': red_flag_count,
                'green_flag_count': green_flag_count
            }

            for r in ['nc_count', 'yellow_flag_count', 'orange_flag_count', 'red_flag_count', 'green_flag_count']:
                project_details.append({'label': r, 'value': vals[r]})
        return project_details

    def floor_name_list(self):
        floors = self.search([])  # Retrieve all project records
        floors_list = []
        for floor in floors:
            floors_list.append(floor.name)
        return floors_list

    # Tower wise nc counts
    @api.model
    def get_floor_counts(self):
        floors = self.search([])  # Retrieve all project records
        floors_details = []
        for floor in floors:
            floors_details.append({'name': floor.name, 'floors_nc': floor.floors_nc,
                                   'floors_yellow': floor.floors_yellow, 'floors_orange': floor.floors_orange,
                                   'floors_red': floor.floors_red, 'floors_green': floor.floors_green})
        floor_list = self.floor_name_list()
        count_list_nc = {}
        count_list_yc = {}
        count_list_oc = {}
        count_list_rc = {}
        count_list_gc = {}

        for r in floors_details:
            count_list_nc[r['name']] = r['floors_nc']
            count_list_yc[r['name']] = r['floors_yellow']
            count_list_oc[r['name']] = r['floors_orange']
            count_list_rc[r['name']] = r['floors_red']
            count_list_gc[r['name']] = r['floors_green']
        graph_result = [{'l_month': 'NC', 'leave': count_list_nc},
                        {'l_month': 'YC', 'leave': count_list_yc},
                        {'l_month': 'OC', 'leave': count_list_oc},
                        {'l_month': 'RC', 'leave': count_list_rc},
                        {'l_month': 'GC', 'leave': count_list_gc}]
        return graph_result, floor_list


class ProjectFlats(models.Model):
    _inherit = "project.flats"

    @api.model
    def get_flats_names(self):
        flats_names = self.env['project.flats'].search_read(
            [], ['name'])  # Fetch only the names
        return flats_names

    @api.model
    def get_all_project_flats(self):
        try:
            all_project_flats = self.env['project.flats'].search([])
            total_flats = len(all_project_flats)
        except Exception as e:
            total_flats = 0
            error_message = _(
                "An error occurred while retrieving project flats count: %s") % str(e)
            # Log the error or handle it appropriately
            _logger.error(error_message)
        return {
            'total_flats': total_flats
        }

    @api.model
    def get_flat_wise_details(self, selected_value):
        project_details = []
        projects = self.search([('id', '=', selected_value)])
        if projects:
            nc_count = 0
            yellow_flag_count = 0
            orange_flag_count = 0
            red_flag_count = 0
            green_flag_count = 0

            for project in projects:
                matched_projects = self.env['manually.set.flag'].search(
                    [('project_flats_id', '=', project.id), ('status', 'in', ['open', 'submit'])
])
                # for matched_project in matched_projects:
                #     nc_count += int(matched_project.cre_nc)
                #     yellow_flag_count += int(matched_project.cre_yellow)
                #     orange_flag_count += int(matched_project.cre_orange)
                #     red_flag_count += int(matched_project.cre_red)
                #     green_flag_count += int(matched_project.cre_Green)
                for matched_project in matched_projects:
                        if matched_project.flag_category == 'Nc':
                            nc_count += 1
                        elif matched_project.flag_category == 'Yellow Flag':
                            yellow_flag_count += 1
                        elif matched_project.flag_category == 'Orange Flag':
                            orange_flag_count += 1
                        elif matched_project.flag_category == 'Red Flag':
                            red_flag_count += 1
                        elif matched_project.flag_category == 'Green Flag':
                            green_flag_count += 1

            vals = {
                'nc_count': nc_count,
                'yellow_flag_count': yellow_flag_count,
                'orange_flag_count': orange_flag_count,
                'red_flag_count': red_flag_count,
                'green_flag_count': green_flag_count
            }

            for r in ['nc_count', 'yellow_flag_count', 'orange_flag_count', 'red_flag_count', 'green_flag_count']:
                project_details.append({'label': r, 'value': vals[r]})
        return project_details

    def flat_name_list(self):
        flats = self.search([])  # Retrieve all project records
        flat_list = []
        for flat in flats:
            flat_list.append(flat.name)
        return flat_list

    # Tower wise nc counts
    @api.model
    def get_flat_counts(self):
        flats = self.search([])  # Retrieve all project records
        flats_details = []
        for flat in flats:
            flats_details.append({'name': flat.name, 'flats_nc': flat.flats_nc,
                                  'flats_yellow': flat.flats_yellow, 'flats_orange': flat.flats_orange,
                                  'flats_red': flat.flats_red, 'flats_green': flat.flats_green})
        flat_list = self.flat_name_list()
        count_list_nc = {}
        count_list_yc = {}
        count_list_oc = {}
        count_list_rc = {}
        count_list_gc = {}
        for r in flats_details:
            count_list_nc[r['name']] = r['flats_nc']
            count_list_yc[r['name']] = r['flats_yellow']
            count_list_oc[r['name']] = r['flats_orange']
            count_list_rc[r['name']] = r['flats_red']
            count_list_gc[r['name']] = r['flats_green']
        graph_result = [{'l_month': 'NC', 'leave': count_list_nc},
                        {'l_month': 'YC', 'leave': count_list_yc},
                        {'l_month': 'OC', 'leave': count_list_oc},
                        {'l_month': 'RC', 'leave': count_list_rc},
                        {'l_month': 'GC', 'leave': count_list_gc}]
        return graph_result, flat_list
