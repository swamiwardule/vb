import datetime

import requests

from odoo import fields
from odoo.http import request, root
from odoo.service import security
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from werkzeug.exceptions import BadRequest
from datetime import datetime, timedelta
import math
import random
import logging
from odoo.http import request, route, Response
import json
from collections import Counter
from pytz import timezone
from odoo import http
import base64
_logger = logging.getLogger(__name__)


def _rotate_session(httprequest):
    if httprequest.session.rotate:
        root.session_store.delete(httprequest.session)
        httprequest.session.sid = root.session_store.generate_key()
        if httprequest.session.uid:
            httprequest.session.session_token = security.compute_session_token(
                httprequest.session, request.env
            )
        httprequest.session.modified = True


class SessionAuthenticationService(Component):
    _inherit = "base.rest.service"
    _name = "session.authenticate.service"
    _usage = "auth"
    _collection = "session.rest.services"

    @restapi.method([(["/login"], "POST")], auth="public")
    def authenticate(self):
        params = request.params
        db_name = params.get("db")
        request.session.authenticate(
            db_name, params["login"], params["password"])
        result = request.env["ir.http"].session_info()
        # avoid to rotate the session outside of the scope of this method
        # to ensure that the session ID does not change after this method
        _rotate_session(request)
        request.session.rotate = False
        expiration = datetime.utcnow() + timedelta(days=90)
        result["session"] = {
            "sid": request.session.sid,
            "expires_at": fields.Datetime.to_string(expiration),
        }
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        base_url = base_url + \
            "/web/image?model=res.users&field=image_1920&id=" + \
            str(result['uid'])
        result['profile_image'] = base_url
        approver_group_id = self.env.ref(
            'custom_project_management.group_quality_approver')
        approver_group_id = self.env['res.groups'].sudo().browse(
            approver_group_id.id)
        checker_group_id = self.env.ref(
            'custom_project_management.group_quality_checker')
        checker_group_id = self.env['res.groups'].sudo().browse(
            checker_group_id.id)

        maker_group_id = self.env.ref(
            'custom_project_management.group_quality_maker')
        maker_group_id = self.env['res.groups'].sudo().browse(
            maker_group_id.id)

        del_activity_group_id = self.env.ref(
            'custom_project_management.group_delete_activity')
        del_activity_group_id = self.env['res.groups'].sudo().browse(
            del_activity_group_id.id)
        result['del_activity_users'] = False
        if result['uid'] in del_activity_group_id.users.ids:
            result['del_activity_users'] = True

        if result['uid'] in approver_group_id.users.ids:
            result['user_type'] = 'approver'
        elif result['uid'] in checker_group_id.users.ids:
            result['user_type'] = 'checker'
        elif result['uid'] in maker_group_id.users.ids:
            result['user_type'] = 'maker'

        else:
            result['user_type'] = 'employee'

        return result

    @restapi.method([(["/signup"], "POST")], auth="public")
    def signup(self):
        params = request.params
        user_id = self.env['res.users'].sudo().search(
            [('login', '=', params["email"])], limit=1)
        if user_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'User already exists', }),
                            content_type='application/json;charset=utf-8', status=200)
        db_name = params.get("db")
        data = {
            'name': params["name"],
            'login': params["email"],
            'password': params["password"]
        }
        if params.get('lat'):
            data.update({
                'lat': params.get('lat')
            })
        if params.get('long'):
            data.update({
                'longi': params.get('long')
            })

        user_id = self.env["res.users"].sudo().create(data)
        user_id.sudo()._change_password(params["password"])
        if params.get('maker'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_maker')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        if params.get('checker'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_checker')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        if params.get('approver'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_approver')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'User Signup Done', }),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/signout"], "POST")], auth="user")
    def get_partner(self):
        partner_id = self.env['res.partner'].sudo().search([])

        return {
            'partner_id': str(partner_id.ids)
        }

    @restapi.method([(["/logout"], "POST")], auth="user")
    def logout(self):
        request.session.logout(keep_db=True)
        return {"message": "Successful logout"}

    @restapi.method([(["/get/assigned/projects"], "POST")], auth="user")
    def get_assigned_projects(self):

        project_ids = self.env['project.info'].sudo().search(
            [('assigned_to_ids', 'in', self.env.user.id)])
        data_dict = []
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        for project in project_ids:
            url = base_url+"/web/image?model=project.info&field=image&id=" + \
                str(project.id)
            # print ("--base_url----",base_url)
            data_dict.append({
                'name': project.name,
                'image': url,
                'project_id': project.id,
                'progress': project.project_progress_bar or 0.0,
            })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data_dict}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/nc"], "POST")], auth="user")
    def get_project_nc(self):

        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        project_data = self.env['project.info'].sudo(
        ).get_project_nc_data(params.get('project_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/tower_floor/nc"], "POST")], auth="user")
    def get_project_tower_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_nc_data(
            params.get('project_id'), params.get('tower_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/floor/nc"], "POST")], auth="user")
    def get_project_tower_floor_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('floor_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_floor_nc_data(
            params.get('project_id'), params.get('tower_id'), params.get('floor_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/activity/nc"], "POST")], auth="user")
    def get_floor_activity_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('floor_id') and not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project, Tower, Floor, Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_floor_activity_nc(params.get(
            'project_id'), params.get('tower_id'), params.get('floor_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/activity_type/nc"], "POST")], auth="user")
    def get_floor_activity_type_nc(self):

        params = request.params

        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity, Type ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_floor_activity_type_nc(
            params.get('activity_id'), params.get('type_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/checklist/nc"], "POST")], auth="user")
    def get_floor_checklist_nc(self):

        params = request.params
        if not params.get('checklist_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo(
        ).get_floor_checklist_nc(params.get('checklist_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # For Flat Start

    @restapi.method([(["/get/project/tower_flat/nc"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_towerflat_nc_data(
            params.get('project_id'), params.get('tower_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/flat/nc"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('flat_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_flat_nc_data(
            params.get('project_id'), params.get('tower_id'), params.get('flat_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/activity/nc"], "POST")], auth="user")
    def get_flat_activity_nc(self):
        _logger.info("--get_flat_activity_nc----")

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('flat_id') and not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project, Tower, Floor, Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_flat_activity_nc(params.get(
            'project_id'), params.get('tower_id'), params.get('flat_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/activity_type/nc"], "POST")], auth="user")
    def get_flat_activity_type_nc(self):

        params = request.params
        if not params.get('activity_id') and not params.get('type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity and Type Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_flat_activity_type_nc(
            params.get('type_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/checklist/nc"], "POST")], auth="user")
    def get_flat_checklist_nc(self):
        params = request.params
        if not params.get('checklist_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo(
        ).get_flat_checklist_nc(params.get('checklist_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # For  Flats End

    @restapi.method([(["/get/project_info"], "POST")], auth="user")
    def get_project_info(self):

        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        project_id = self.env['project.info'].sudo().browse(
            int(params.get('project_id')))
        if not project_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        project_image_url = base_url + \
            "/web/image?model=project.info&field=image&id="+str(project_id.id)
        data = {
            'project_name': project_id.name,
            'image_url': project_image_url,
        }

        list_data = []
        for project_info in project_id.project_details_line:
            line_url = base_url+"/web/image?model=project.details&field=image&id=" + \
                str(project_info.id)
            list_data.append({
                'name': project_info.name,
                'image': line_url,
                'checklist_id': project_info.id,
            })
        data['checklist_data'] = list_data

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/checklist/tower"], "POST")], auth="user")
    def get_checklist_tower(self):
        params = request.params
        user_id = False
        list_data = []
        progress = 0.0
        if params.get('user_id'):
            user_id = params.get('user_id')
        if not params.get('checklist_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        checklist_id = self.env['project.details'].sudo().browse(
            int(params.get('checklist_id')))
        if not checklist_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        checklist_image_url = base_url + \
            "/web/image?model=project.details&field=image&id=" + \
            str(checklist_id.id)

        data = {
            'checklist_name': checklist_id.name,
            'image_url': checklist_image_url,
            'checklist_id': checklist_id.id,
            # 'progress':checklist_id.project_id.project_progress_bar or 0.0,
        }

        for tower in checklist_id.tower_id:
            progress = tower.project_id.project_progress_bar or 0.0
            # _logger.info("---------6666------")
            user_ids = list(tower.assigned_to_ids.ids)
            if int(user_id) in user_ids:
                list_data.append({
                    'name': tower.name,
                    'tower_id': tower.id,
                    'progress': tower.tower_progress_percentage,  # prject overall progress

                })
        data.update({'progress': progress})
        data['tower_data'] = list_data
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/checklist/count"], "POST")], auth="user")
    def get_tower_checklist_count(self):
        params = request.params
        if not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        tower_id = self.env['project.tower'].sudo().browse(
            int(params.get('tower_id')))
        if not tower_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        data = {
            'tower_name': tower_id.name,
            'tower_id': tower_id.id
        }
        floor_data = []
        for floor in tower_id.tower_floor_line_id:
            submit_count = checked_count = approve_count = 0

            for activity in floor.activity_ids:

                status_counts = Counter(
                    act_type.status for act_type in activity.activity_type_ids)
                submit_count = status_counts.get('submit', 0)
                checked_count = status_counts.get('checked', 0)
                approve_count = status_counts.get('approve', 0)

                # for act_type in activity.activity_type_ids:
                #     status = act_type.status
                #     if status == 'submit':
                #         submit_count += 1
                #     if status == 'checked':
                #         checked_count += 1
                #     if status == 'approve':
                #         approve_count += 1

            floor_data.append({
                'name': floor.name,
                'floor_id': floor.id,
                'maker_count': submit_count,
                'checker_count': checked_count,
                'approver_count': approve_count,

            })
        data['floor_data'] = floor_data
        flat_data = []
        for flat in tower_id.tower_flat_line_id:
            submit_count = checked_count = approve_count = 0
            for activity in flat.activity_ids:

                status_counts = Counter(
                    act_type.status for act_type in activity.activity_type_ids)
                submit_count = status_counts.get('submit', 0)
                checked_count = status_counts.get('checked', 0)
                approve_count = status_counts.get('approve', 0)

            flat_data.append({
                'name': flat.name,
                # this should be flat_id
                'floor_id': flat.id,
                'maker_count': submit_count,
                'checker_count': checked_count,
                'approver_count': approve_count,
            })

        data['flat_data'] = flat_data

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower info Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/floor"], "POST")], auth="user")
    def get_flat_floor_by_tower_test(self):
        params = request.params
        if not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        tower_id = self.env['project.tower'].sudo().browse(
            int(params.get('tower_id')))
        if not tower_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        data = {
            "tower_name": tower_id.name,
            "tower_id": tower_id.id,
            "progress": tower_id.tower_progress_percentage,  # tower progress
        }

        flat_maker = flat_checker = flat_approver = flat_checklist = 0
        floor_maker = floor_checker = floor_approver = floor_checklist = 0

        floor_data = []
        for floor in tower_id.tower_floor_line_id:
            submit_count = checked_count = approve_count = total_checklist_count = 0

            for activity in floor.activity_ids:
                for act_type in activity.activity_type_ids:
                    status = act_type.status
                    total_checklist_count += 1
                    if status == 'submit':
                        submit_count += 1
                    if status == 'checked':
                        checked_count += 1
                    if status == 'approve':
                        approve_count += 1

            floor_maker += submit_count+checked_count+approve_count
            floor_checker += checked_count+approve_count
            floor_approver += approve_count
            floor_checklist += total_checklist_count

            floor_data.append({
                "name": floor.name,
                "floor_id": floor.id,
                "progress": floor.floor_progress_percentage or 0.0,
                "total_count": total_checklist_count,
                # "maker_count": submit_count,
                # "checker_count": checked_count,
                # "approver_count": approve_count,
                "maker_count": submit_count+checked_count+approve_count,
                "checker_count": checked_count+approve_count,
                "approver_count": approve_count,
            })

        floor_total = floor_checklist
        flat_data = []
        for flat in tower_id.tower_flat_line_id:
            submit_count = checked_count = approve_count = total_checklist_count = 0
            for activity in flat.activity_ids:
                for act_type in activity.activity_type_ids:
                    status = act_type.status
                    total_checklist_count += 1
                    if status == 'submit':
                        submit_count += 1
                    if status == 'checked':
                        checked_count += 1
                    if status == 'approve':
                        approve_count += 1

            flat_maker += submit_count+checked_count+approve_count
            flat_checker += checked_count+approve_count
            flat_approver += approve_count
            flat_checklist += total_checklist_count

            flat_data.append({
                "name": flat.name,
                "flat_id": flat.id,
                "progress": flat.flats_progress_percentage or 0.0,
                "total_count": total_checklist_count,
                # "maker_count": submit_count,
                # "checker_count": checked_count,
                # "approver_count": approve_count,
                "maker_count": submit_count+checked_count+approve_count,
                "checker_count": checked_count+approve_count,
                "approver_count": approve_count,
            })

        flat_total = flat_checklist
        data["tower_total_count"] = flat_total+floor_total
        data["tower_maker_count"] = flat_maker+floor_maker
        data["tower_checker_count"] = flat_checker+floor_checker
        data["tower_approver_count"] = flat_approver+floor_approver
        data["flat_total_count"] = flat_total
        data["flat_maker_count"] = flat_maker
        data["flat_checker_count"] = flat_checker
        data["flat_approver_count"] = flat_approver
        data["floor_total_count"] = floor_total
        data["floor_maker_count"] = floor_maker
        data["floor_checker_count"] = floor_checker
        data["floor_approver_count"] = floor_approver
        data['list_flat_data'] = flat_data
        data['list_floor_data'] = floor_data

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower info Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/activites"], "POST")], auth="user")
    def get_flat_activites(self):
        params = request.params
        if not params.get('flat_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        flat_id = self.env['project.flats'].sudo().browse(
            int(params.get('flat_id')))
        if not flat_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = {
            'flat_name': flat_id.name,
            'flat_id': flat_id.id
        }

        list_flat_data = []
        total_count = 0
        for activity in flat_id.activity_ids:

            count = draft = checked = approve = 0
            color = 'yellow'
            activity_type_status = False

            for act_type in activity.activity_type_ids:
                status = act_type.status
                count += 1
                if status == 'draft':
                    draft += 1
                if status == 'checked':
                    checked += 1
                if status == 'approve':
                    approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            if approve and not draft and not checked:
                color = 'green'
                activity_type_status = True

            list_flat_data.append({
                'name': activity.name,
                'desc': '',
                'activity_id': activity.id,
                'write_date': str(activity.write_date),
                'activity_type_status': activity_type_status,
                'progress': activity.progress_percentage or 0.0,
                'color': color,
            })
        data['list_flat_data'] = list_flat_data
        data['total_count'] = total_count

        # _logger.info("-----data------,%s",data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/activites"], "POST")], auth="user")
    def get_floor_activites(self):
        params = request.params
        if not params.get('floor_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        floor_id = self.env['project.floors'].sudo().browse(
            int(params.get('floor_id')))
        if not floor_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Floor ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = {
            'floor_name': floor_id.name,
            'floor_id': floor_id.id
        }
        list_floor_data = []
        total_count = 0
        for activity in floor_id.activity_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            activity_type_status = False

            for act_type in activity.activity_type_ids:
                status = act_type.status
                count += 1
                if status == 'draft':
                    draft += 1
                if status == 'checked':
                    checked += 1
                if status == 'approve':
                    approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            if approve and not draft and not checked:
                color = 'green'
                activity_type_status = True

            list_floor_data.append({
                'name': activity.name,
                'desc': '',
                'activity_id': activity.id,
                'write_date': str(activity.write_date),
                'activity_type_status': activity_type_status,
                'progress': activity.progress_percentage or 0.0,
                'color': color,
            })
        data['list_floor_data'] = list_floor_data
        data['total_count'] = total_count

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

# color coding
# color coding
    @restapi.method([(["/get/checklist"], "POST")], auth="public")
    def get_checklist_by_activity(self):
        params = request.params
        user_id = ''
        role = ''

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_id = self.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        if not activity_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        _logger.info(
            "-------------------activity_id:-----------------", activity_id)
        data = {
            'activity_name': activity_id.name,
            'activity_id': activity_id.id,
            'activity_progress': activity_id.progress_percentage,
            'project_id': activity_id.project_id.id,
            'project_name': activity_id.project_id.name,
            'tower_id': activity_id.tower_id.id,
            'tower_name': activity_id.tower_id.name,
            'floor_id': activity_id.floor_id.id,
            'floor_name': activity_id.floor_id.name,
        }

        # _logger.info("------------------data----------------------", data)

        list_checklist_data = []
        list_checklist_line = []

        # pre,during,post
        total_count = 0

        for activity in activity_id.activity_type_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            reject = ''
            if activity.type_status:
                if activity.type_status == 'checker_reject' or activity.type_status == 'approver_reject':
                    reject = activity.type_status
                    _logger.info("=================activity.type_status=============,%s", reject)

            status = activity.status
            color = 'yellow'  # Default color
            if status in ['draft', 'submit', 'checker_reject']:
                color = 'red'
            elif status == 'checked':
                color = 'yellow'
            elif status == 'approve':
                color = 'green'

            line_data = []
            # logs = self.env['project.checklist.line.log'].search([('activity_type_id','=',activity.id)])
            for checklist_line in activity.checklist_ids:
                history = []
                log_lines = self.env['project.checklist.line.log'].search(
                    [('line_id', '=', checklist_line.id)])

                for line in log_lines:
                    image_link = []
                    for url in line.checklist_line_log_line:
                        # Generate HTTP URL for log line images or use existing URL
                        if hasattr(url, 'url') and url.url:
                            image_link.append(url.url)
                        elif hasattr(url, 'id'):
                            # Generate HTTP URL if only ID is available
                            log_image_url = str(base_url) + "/web/image?model=project.checklist.line.log.line&field=image&id=" + str(url.id)
                            image_link.append(log_image_url)
                    
                    history.append({
                        'id': line.id,
                        'name': line.checklist_template_id.name,
                        'reason': line.reason,
                        'is_pass': line.is_pass,
                        'name': line.checklist_template_id.name,
                        'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                        'update_time': str(line.datetime),
                        'image_url': image_link,
                        'submitted': 'false',
                    })

                image_link = []
                for image_line in checklist_line.image_ids:
                    # if image_line.image=='':
                        checklist_image_url = str(
                            base_url)+"/web/image?model=project.checklist.line.images&field=image&id="+str(image_line.id)
                        image_link.append({'url':checklist_image_url,'img_desc':image_line.img_desc or ''})
                                    
                line_data.append({
                    'name': checklist_line.checklist_template_id.name,
                    'reason': checklist_line.reason,
                    'is_pass': checklist_line.is_pass,
                    'name': checklist_line.checklist_template_id.name,
                    'image_url': image_link,
                    'line_id': checklist_line.id,
                    'history': history
                    # 'submittedBy':{'id':user_id,'name':user_record.name,'role':role},
                    # 'update_time':datetime.datetime.now(),
                })

            activity_status = activity.type_status
            _logger.info("-------activity_status-----,%s", activity_status)

            try:
                # image_urls = []
                # if activity.activity_type_img_ids:
                #     for img in activity.activity_type_img_ids:
                #         if img.img_type == 'pat':
                #             checklist_image_url = str(
                #                 base_url)+"/web/image?model=project.activity.type.image&field=overall_img&id="+str(img.id)
                #             image_urls.append(str(checklist_image_url))

                image_urls = []
                if activity.activity_type_img_ids:
                    for img in activity.activity_type_img_ids:
                        if img.img_type == 'pat':
                            # img_base64 = ''
                            # if img.overall_img:
                            #     if isinstance(img.overall_img, bytes):
                            #         img_base64 = base64.b64encode(img.overall_img).decode('utf-8')
                            #     else:
                            #         img_base64 = img.overall_img
                            checklist_image_url = str(
                            base_url)+"/web/image?model=project.activity.type.image&field=overall_img&id="+str(img.id)
                            image_urls.append({
                                'url': checklist_image_url,
                                'img_desc': img.img_desc or '',
                                # 'img_type': img.img_type or '',
                                # 'custom_url': img.url or ''
                            })

            except Exception as e:
                _logger.info(
                    "-get_project_activity_details--exception- overall_images-----,%s", str(e))
                image_urls = []  # Ensure image_urls is always defined
                pass

            list_checklist_data.append({
                'name': activity.name,
                'activity_type_id': activity.id,
                'activity_status': activity_status,
                'activity_type_progress': activity.progress_percentage,
                'project_id': activity.project_id.id,
                'project_name': activity.project_id.name,
                'flat': activity.flat_id.id,
                'flat_name': activity.flat_id.name,
                'tower_id': activity.tower_id.id,
                'tower_name': activity.tower_id.name,
                'floor_id': activity.floor_id.id,
                'floor_name': activity.floor_id.name,
                'overall_remarks': activity.overall_remarks or '',
                'overall_remarks_maker': activity.overall_remarks_maker or '',
                'overall_remarks_checker': activity.overall_remarks_checker or '',
                'overall_remarks_approver': activity.overall_remarks_approver or '',
                'overall_images': image_urls,
                'line_data': line_data,
                'color': color,
                'wi_status': reject,
            })

        data['list_checklist_data'] = list_checklist_data
        # _logger.info("-----dataaaaaaa----,%s", str(data))

        # data['color'] = color

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist info Fetch', 'checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)
   
    # @restapi.method([(["/get/checklist"], "POST")], auth="public")
    # def get_checklist_by_activity(self):
    #     params = request.params
    #     user_id = ''
    #     role = ''

    #     get_param = self.env['ir.config_parameter'].sudo().get_param
    #     base_url = get_param(
    #         'web.base.url', default='http://www.odoo.com?NoBaseUrl')

    #     if not params.get('activity_id'):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     activity_id = self.env['project.activity'].sudo().browse(
    #         int(params.get('activity_id')))
    #     if not activity_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)

    #     _logger.info(
    #         "-------------------activity_id:-----------------", activity_id)
    #     data = {
    #         'activity_name': activity_id.name,
    #         'activity_id': activity_id.id,
    #         'activity_progress': activity_id.progress_percentage,
    #         'project_id': activity_id.project_id.id,
    #         'project_name': activity_id.project_id.name,
    #         'tower_id': activity_id.tower_id.id,
    #         'tower_name': activity_id.tower_id.name,
    #         'floor_id': activity_id.floor_id.id,
    #         'floor_name': activity_id.floor_id.name,
    #     }

    #     # _logger.info("------------------data----------------------", data)

    #     list_checklist_data = []
    #     list_checklist_line = []

    #     # pre,during,post
    #     total_count = 0

    #     for activity in activity_id.activity_type_ids:
    #         count = draft = checked = approve = 0
    #         color = 'yellow'
    #         reject = ''
    #         if activity.type_status:
    #             if activity.type_status == 'checker_reject' or activity.type_status == 'approver_reject':
    #                 reject = activity.type_status

    #         status = activity.status
    #         count += 1
    #         if status == 'draft':
    #             draft += 1
    #         if status == 'checked':
    #             checked += 1
    #         if status == 'approve':
    #             approve += 1

    #         total_count += count
    #         if draft and not checked and not approve:
    #             color = 'red'
    #         if approve and not draft and not checked:
    #             color = 'green'

    #         line_data = []
    #         # logs = self.env['project.checklist.line.log'].search([('activity_type_id','=',activity.id)])
    #         for checklist_line in activity.checklist_ids:
    #             history = []
    #             log_lines = self.env['project.checklist.line.log'].search(
    #                 [('line_id', '=', checklist_line.id)])

    #             for line in log_lines:
    #                 image_link = []
    #                 for url in line.checklist_line_log_line:
    #                     # _logger.info("-url------,%s",str(url))
    #                     image_link.append(url.url)
    #                 history.append({
    #                     'id': line.id,
    #                     'name': line.checklist_template_id.name,
    #                     'reason': line.reason,
    #                     'is_pass': line.is_pass,
    #                     'name': line.checklist_template_id.name,
    #                     'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
    #                     'update_time': str(line.datetime),
    #                     'image_url': image_link,
    #                     'submitted': 'false',
    #                 })

    #             image_link = []
    #             for image_line in checklist_line.image_ids:
    #                 checklist_image_url = str(
    #                     base_url)+"/web/image?model=project.checklist.line.images&field=image&id="+str(image_line.id)
    #                 image_link.append(checklist_image_url)

    #             line_data.append({
    #                 'name': checklist_line.checklist_template_id.name,
    #                 'reason': checklist_line.reason,
    #                 'is_pass': checklist_line.is_pass,
    #                 'name': checklist_line.checklist_template_id.name,
    #                 'image_url': image_link,
    #                 'line_id': checklist_line.id,
    #                 'history': history
    #                 # 'submittedBy':{'id':user_id,'name':user_record.name,'role':role},
    #                 # 'update_time':datetime.datetime.now(),
    #             })

    #         activity_status = activity.status
    #         if activity.status == 'approver_reject':
    #             # activity_status = 'submit'
    #             activity_status = 'approver_reject'

    #         if activity.status == 'checker_reject':
    #             activity_status = 'draft'

    #         try:
    #             image_urls = []
    #             if activity.activity_type_img_ids:
    #                 for img in activity.activity_type_img_ids:
    #                     if img.img_type == 'pat':
    #                         checklist_image_url = str(
    #                             base_url)+"/web/image?model=project.activity.type.image&field=overall_img&id="+str(img.id)
    #                         image_urls.append(str(checklist_image_url))
    #         except Exception as e:
    #             _logger.info(
    #                 "-get_project_activity_details--exception- overall_images-----,%s", str(e))
    #             pass
    #         # _logger.info("-------color-----,%s",str(color))

    #         list_checklist_data.append({
    #             'name': activity.name,
    #             'activity_type_id': activity.id,
    #             'activity_status': activity_status,
    #             'activity_type_progress': activity.progress_percentage,
    #             'project_id': activity.project_id.id,
    #             'project_name': activity.project_id.name,
    #             'flat': activity.flat_id.id,
    #             'flat_name': activity.flat_id.name,
    #             'tower_id': activity.tower_id.id,
    #             'tower_name': activity.tower_id.name,
    #             'floor_id': activity.floor_id.id,
    #             'floor_name': activity.floor_id.name,
    #             'overall_remarks': activity.overall_remarks or '',
    #             'overall_images': image_urls,
    #             'line_data': line_data,
    #             'color': color,
    #             'wi_status': reject,
    #         })

    #     data['list_checklist_data'] = list_checklist_data
    #     _logger.info("-----dataaaaaaa----,%s", str(data))

    #     # data['color'] = color

    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist info Fetch', 'checklist_data': data}),
    #                     content_type='application/json;charset=utf-8', status=200)

    # AAAAAA overall remark - 2 images -


#disha 
    @restapi.method([(["/maker/checklist/update"], "POST")], auth="user")
    def update_checklist_maker(self):
        pr_act_ty_img_obj = self.env['project.activity.type.image']
        params = request.params
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')

        _logger.info("---------update_checklist_maker---------,%s", params)

        user_id = params.get('user_id', False)
        send_notification = str(params.get('is_draft', 'yes')) == 'no'

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Invalid Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        if params.get('overall_remarks_maker'):
            activity_type_id.write({'overall_remarks_maker': params.get('overall_remarks_maker')})

        seq_no = activity_type_id.seq_no

        # Handle overall images
        try:
            if params.get('overall_images'):
                images = params.get('overall_images')
                data = []
                for img in images:
                    # img can be dict or string
                    if isinstance(img, dict):
                        overall_img = img.get('image')
                        img_desc = img.get('img_desc', False)

                        _logger.info("---------img_desc-(overall image--------,%s", img_desc)
                        
                    else:
                        overall_img = img
                        img_desc = False

                    if overall_img:
                        missing_padding = len(overall_img) % 4
                        if missing_padding:
                            overall_img += '=' * (4 - missing_padding)

                        data.append({
                            'activity_type_id': activity_type_id.id,
                            'overall_img': overall_img,
                            'img_type': 'pat',
                            'img_desc': img_desc
                        })
                if data:
                    pr_act_ty_img_obj.create(data)
        except Exception as e:
            _logger.info("---exception- overall_images-----,%s", str(e))

        if activity_type_id and user_id:
            activity_type_id.user_maker = user_id

        # Handle checklist lines
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []

                checklist_id = self.env['project.checklist.line'].sudo().browse(int(line.get('line_id')))
                if not checklist_id:
                    continue

                checklist_id.write({'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})

                # Handle images
                attachment_vals_list = []
                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        # support dict {'image':..., 'img_desc':...} or just string
                        if isinstance(image_data, dict):
                            img_base64 = image_data.get('image')
                            img_desc = image_data.get('img_desc', False)
                        else:
                            img_base64 = image_data 
                            img_desc = False

                        _logger.info("---------img_desc-(checklist line)--------,%s", img_desc)


                        if img_base64:
                            missing_padding = len(img_base64) % 4
                            if missing_padding:
                                img_base64 += '=' * (4 - missing_padding)

                            attachment_vals_list.append((0, 0, {
                                'image': img_base64,
                                'img_desc': img_desc
                            }))
                            image_datas.append(img_base64)

                    if attachment_vals_list:
                        checklist_id.write({'image_ids': attachment_vals_list})

                # Collect image URLs
                for img in checklist_id.image_ids:
                    checklist_image_url = f"{base_url}/web/image?model=project.checklist.line.images&field=image&id={img.id}"
                    image_urls.append(checklist_image_url)

                # Send notifications if needed
                if send_notification:
                    data = {
                        'line_id': int(line.get('line_id')),
                        'checklist_template_id': checklist_id.checklist_template_id.id,
                        'role': 'maker',
                        'status': activity_type_id.status,
                        'activity_type_id': activity_type_id.id,
                        'project_id': activity_type_id.project_id.id,
                        'user_id': user_id,
                        'is_pass': line.get('is_pass'),
                        'reason': line.get('reason'),
                        'seq_no': seq_no,
                        'overall_remarks': activity_type_id.overall_remarks_maker
                    }
                    pcl_log = self.env['project.checklist.line.log'].create(data)

                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create({'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})

                    for url in image_urls:
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        # Submit activity if needed
        if send_notification:
            activity_type_id.sudo().button_submit(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)




# swami's code
    # @restapi.method([(["/maker/checklist/update"], "POST")], auth="user")
    # def update_checklist_maker(self):
    #     pr_act_ty_img_obj = self.env['project.activity.type.image']
    #     # maker will update the checklist and click on submit button notification should sent to res. checker
    #     seq_no = 0
    #     params = request.params
    #     get_param = self.env['ir.config_parameter'].sudo().get_param
    #     base_url = get_param(
    #         'web.base.url', default='http://www.odoo.com?NoBaseUrl')
    #     _logger.info("---------update_checklist_maker---------,%s", params)
    #     user_id = False
    #     send_notification = False
    #     if params.get('is_draft'):
    #         # _logger.info("---------params--------,%s", params)
    #         value = str(params.get('is_draft'))
    #         if value == 'no':
    #             send_notification = True
    #     try:
    #         if params.get('user_id'):
    #             user_id = params.get('user_id')
    #     except:
    #         pass
    #     if not params.get('activity_type_id'):
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     activity_type_id = self.env['project.activity.type'].sudo().browse(
    #         int(params.get('activity_type_id')))
    #     if params.get('overall_remarks_maker'):
    #         activity_type_id.write(
    #             {'overall_remarks_maker': params.get('overall_remarks_maker')})
    #     if not activity_type_id:
    #         return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
    #                         content_type='application/json;charset=utf-8', status=201)
    #     seq_no = activity_type_id.seq_no

    #     try:
    #         if params.get('overall_images'):
    #             images = params.get('overall_images')
    #             data = []
    #             for img in images:
    #                 temp = {'activity_type_id': activity_type_id.id,
    #                         'overall_img': img.get('image'), 'img_type': 'pat','img_desc': img.get('img_desc', False)}
    #                 data.append(temp)
    #             if data:
    #                 pr_act_ty_img_obj.create(data)
    #     except Exception as e:
    #         _logger.info("---exception- overall_images-----,%s", str(e))
    #         pass

    #     if activity_type_id and user_id:
    #         activity_type_id.user_maker = user_id

    #     if params.get('checklist_line'):
    #         for line in params.get('checklist_line'):
    #             image_datas = []
    #             image_urls = []
    #             checklist_id = self.env['project.checklist.line'].sudo().browse(
    #                 int(line.get('line_id')))
    #             if checklist_id:
    #                 checklist_id.write(
    #                     {'is_pass': line.get('is_pass'), 'submitted': 'false'})
    #             if line.get('reason'):
    #                 checklist_id.write({'reason': line.get('reason')})

    #             # if line.get('image_data'):
    #             #     for image_data in line.get('image_data'):
    #             #         attachment_vals_list = []
    #             #         attachment_vals_list.append(
    #             #             (0, 0, {'image': image_data}))
    #             #         # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
    #             #         # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
    #             #         checklist_id.write({'image_ids': attachment_vals_list})
    #             #         image_datas.append(image_data)

    #             # if line.get('image_data'):
    #             #     for image_data in line.get('image_data'):
    #             #         attachment_vals_list = []
    #             #         attachment_vals_list.append(
    #             #             (0, 0, {
    #             #                 'image': image_data.get('image'),
    #             #                 'img_desc': image_data.get('img_desc', False)  # Add img_desc
    #             #             }))
    #             #         checklist_id.write({'image_ids': attachment_vals_list})
    #             #         image_datas.append(image_data.get('image'))

    #             if line.get('image_data'):
    #                 attachment_vals_list = []
    #                 for image_data in line.get('image_data'):
    #                     image = image_data.get('image')
    #                     if image:  
    #                         # Fix padding if needed
    #                         missing_padding = len(image) % 4
    #                         if missing_padding:
    #                             image += '=' * (4 - missing_padding)

    #                         attachment_vals_list.append(
    #                             (0, 0, {
    #                                 'image': image,
    #                                 'img_desc': image_data.get('img_desc', False)
    #                             })
    #                         )
    #                         image_datas.append(image)

    #                 if attachment_vals_list:
    #                     checklist_id.write({'image_ids': attachment_vals_list})
              
    #             for img in checklist_id.image_ids:
    #                 checklist_image_url = base_url + \
    #                     "/web/image?model=project.checklist.line.images&field=image&id=" + \
    #                     str(img.id)
    #                 image_urls.append(checklist_image_url)
    #             # print ("--image_datas---",image_datas)
    #             # _logger.info("----- No -------,%s",send_notification)

    #             if send_notification:
    #                 data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'maker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
    #                         'is_pass': line.get('is_pass'),
    #                         'reason': line.get('reason'), 'seq_no': seq_no,
    #                         'overall_remarks': activity_type_id.overall_remarks_maker}
    #                 pcl_log = self.env['project.checklist.line.log'].create(
    #                     data)
    #                 # _logger.info("----- image datas -------,%s",len(image_datas))

    #                 for image in image_datas:
    #                     image_id = self.env['ir.attachment'].create(
    #                         {'datas': image, 'name': 'image'})
    #                     pcl_log.write({'image_ids': [(4, image_id.id)]})
    #                 # _logger.info("----- image_urls -------,%s",len(image_urls))

    #                 for url in image_urls:
    #                     self.env['project.checklist.line.log.line'].create(
    #                         {'url': url, 'project_checklist_line_log_id': pcl_log.id})

    #     # user_id = int(params.get('user_id')) or False
    #     # submitting form and sending notification

    #     if send_notification:
    #         activity_type_id.sudo().button_submit(seq_no, user_id)
    #     # Maintining Log Details
    #     return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
    #                     content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/checklist/reject"], "POST")], auth="user")
    def update_checklist_reject_checker(self):
        # Checker reject the checklist , notification to maker
        params = request.params
        seq_no = False
        user_id = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        # _logger.info("---------update_checklist_reject_checker---------,%s", params)

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        # user_id = int(params.get('user_id')) or False
        if params.get('overall_remarks_checker'):
            activity_type_id.write(
                {'overall_remarks_checker': params.get('overall_remarks_checker'),
                 'status': 'checker_reject'})
        seq_no = activity_type_id.seq_no
        if activity_type_id and user_id:
            activity_type_id.user_checker = user_id
        # _logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    # seq_no = checklist_id.activity_type_id.seq_no
                    # _logger.info("-----seq_no-------,%s",seq_no)

                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                # if line.get('image_data'):
                #     for image_data in line.get('image_data'):
                #         attachment_vals_list = []
                #         attachment_vals_list.append(
                #             (0, 0, {'image': image_data}))
                #         # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                #         # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                #         checklist_id.write({'image_ids': attachment_vals_list})
                #         image_datas.append(image_data)

                # if line.get('image_data'):
                #     for image_data in line.get('image_data'):
                #         attachment_vals_list = []
                #         attachment_vals_list.append(
                #             (0, 0, {
                #                 'image': image_data.get('image'),
                #                 'img_desc': image_data.get('img_desc', False)  # Add img_desc
                #             }))
                #         checklist_id.write({'image_ids': attachment_vals_list})
                #         image_datas.append(image_data.get('image'))

                if line.get('image_data'):
                    attachment_vals_list = []
                    for image_data in line.get('image_data'):
                        # Check if image_data is a string or dictionary
                        if isinstance(image_data, str):
                            # If it's a string, treat it as base64 image directly
                            image = image_data
                            img_desc = ''
                        elif isinstance(image_data, dict):
                            # If it's a dictionary, extract image and description
                            image = image_data.get('image')
                            img_desc = image_data.get('img_desc', '')
                        else:
                            # Skip if it's neither string nor dict
                            continue
                        
                        if image:  
                            # Fix padding if needed
                            missing_padding = len(image) % 4
                            if missing_padding:
                                image += '=' * (4 - missing_padding)

                            attachment_vals_list.append(
                                (0, 0, {
                                    'image': image,
                                    'img_desc': img_desc or False
                                })
                            )
                            image_datas.append(image)
                    
                    # Write attachments to checklist line if any exist
                    if attachment_vals_list:
                        checklist_id.write({'image_ids': attachment_vals_list})


                        

                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)

                data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'checker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                        'is_pass': line.get('is_pass'),
                        'reason': line.get('reason'), 'seq_no': seq_no,
                        'overall_remarks': activity_type_id.overall_remarks_checker}
                pcl_log = self.env['project.checklist.line.log'].create(data)
                for image in image_datas:
                    image_id = self.env['ir.attachment'].create(
                        {'datas': image, 'name': 'image'})
                    pcl_log.write({'image_ids': [(4, image_id.id)]})
                for url in image_urls:
                    _logger.info("-----url checker reject------,%s", url)
                    self.env['project.checklist.line.log.line'].create(
                        {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        activity_type_id.sudo().button_set_to_maker(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checker Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/checklist/update"], "POST")], auth="user")
    def update_checklist_checker(self):
        # this method will get call from checekr to updte the checklist and submit. notification to approver
        params = request.params
        seq_no = False
        user_id = False
        send_notification = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        # _logger.info("---------update_checklist_checker---------,%s", params)

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        if activity_type_id and user_id:
            activity_type_id.user_checker = user_id

        if params.get('overall_remarks_checker'):
            activity_type_id.write(
                {'overall_remarks_checker': params.get('overall_remarks_checker')})
        seq_no = activity_type_id.seq_no
        # if activity_type_id.activity_id and user_id:
        #     activity_type_id.activity_id.user_checker = user_id
        # _logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                # print('-------overall_remarks-----\n\n\n\n\n', checklist_id)
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                # if line.get('overall_remarks'):
                #     checklist_id.write({'overall_remarks':line.get('overall_remarks')})
                # if line.get('image_data'):
                #     for image_data in line.get('image_data'):
                #         attachment_vals_list = []
                #         attachment_vals_list.append(
                #             (0, 0, {'image': image_data}))
                #         # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                #         # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                #         checklist_id.write({'image_ids': attachment_vals_list})
                #         image_datas.append(image_data)

                # if line.get('image_data'):
                #     for image_data in line.get('image_data'):
                #         attachment_vals_list = []
                #         attachment_vals_list.append(
                #             (0, 0, {
                #                 'image': image_data.get('image'),
                #                 'img_desc': image_data.get('img_desc', False)  # Add img_desc
                #             }))
                #         checklist_id.write({'image_ids': attachment_vals_list})
                #         image_datas.append(image_data.get('image'))

                # if line.get('image_data'):
                #     attachment_vals_list = []
                #     for image_data in line.get('image_data'):
                #         image = image_data.get('image')
                #         if image:  
                #             # Fix padding if needed
                #             missing_padding = len(image) % 4
                #             if missing_padding:
                #                 image += '=' * (4 - missing_padding)

                #             attachment_vals_list.append(
                #                 (0, 0, {
                #                     'image': image,
                #                     'img_desc': image_data.get('img_desc', False)
                #                 })
                #             )
                #             image_datas.append(image) 

                if line.get('image_data'):
                    attachment_vals_list = []
                    for image_data in line.get('image_data'):
                        # Handle both string and dictionary formats
                        if isinstance(image_data, str):
                            # If image_data is a string (base64), treat it as the image directly
                            image = image_data
                            img_desc = ''
                        elif isinstance(image_data, dict):
                            # If image_data is a dictionary, extract image and description
                            image = image_data.get('image', '')
                            img_desc = image_data.get('img_desc', '')
                        else:
                            # Skip invalid data
                            _logger.warning("Invalid image_data format: %s", type(image_data))
                            continue
                        
                        if image:  
                            # Fix padding if needed
                            missing_padding = len(image) % 4
                            if missing_padding:
                                image += '=' * (4 - missing_padding)
                            attachment_vals_list.append(
                                (0, 0, {
                                    'image': image,
                                    'img_desc': img_desc
                                })
                            )
                            image_datas.append(image)
                    
                    # Write all attachments at once if any exist
                    # if attachment_vals_list:
                    #     checklist_id.write({'image_ids': attachment_vals_list})                            




                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                if send_notification:
                    data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'checker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                            'is_pass': line.get('is_pass'),
                            'reason': line.get('reason'), 'seq_no': seq_no,
                            'overall_remarks': activity_type_id.overall_remarks_checker}
                    pcl_log = self.env['project.checklist.line.log'].create(
                        data)
                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create(
                            {'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})
                    for url in image_urls:
                        _logger.info("-checker update----url------,%s", url)
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        # user_id = int(params.get('user_id')) or False
        # submitting form and sending notification
        if send_notification:
            activity_type_id.sudo().button_checking_done(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update', 'status': 'Maker'}),
                        content_type='application/json;charset=utf-8', status=200)
    

    @restapi.method([(["/approver/checklist/reject"], "POST")], auth="user")
    def update_checklist_reject(self):
        # Approver will reject the checklist and go back to checker q.o
        params = request.params
        # *logger.info("---------update*checklist_reject---------,%s", params)
        seq_no = False
        user_id = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))
        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        if params.get('overall_remarks_approver'):
            activity_type_id.write(
                {'overall_remarks_approver': params.get('overall_remarks_approver'),
                 'status': 'approver_reject'})
        if activity_type_id and user_id:
            activity_type_id.user_approver = user_id
        seq_no = activity_type_id.seq_no
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                
                if line.get('image_data'):
                    attachment_vals_list = []
                    for image_data in line.get('image_data'):
                        # Handle both string and dictionary formats
                        if isinstance(image_data, str):
                            # If image_data is a string (base64), treat it as the image directly
                            image = image_data
                            img_desc = ''
                        elif isinstance(image_data, dict):
                            # If image_data is a dictionary, extract image and description
                            image = image_data.get('image', '')
                            img_desc = image_data.get('img_desc', '')
                        else:
                            # Skip invalid data
                            _logger.warning("Invalid image_data format: %s", type(image_data))
                            continue
                        
                        if image:  
                            # Fix padding if needed
                            missing_padding = len(image) % 4
                            if missing_padding:
                                image += '=' * (4 - missing_padding)
                            attachment_vals_list.append(
                                (0, 0, {
                                    'image': image,
                                    'img_desc': img_desc
                                })
                            )
                            image_datas.append(image)
                    
                    # Write all attachments at once if any exist
                    if attachment_vals_list:
                        checklist_id.write({'image_ids': attachment_vals_list})
                
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                
                data = {
                    'line_id': int(line.get('line_id')), 
                    'checklist_template_id': checklist_id.checklist_template_id.id, 
                    'role': 'approver', 
                    'status': activity_type_id.status, 
                    'activity_type_id': activity_type_id.id, 
                    'project_id': activity_type_id.project_id.id, 
                    'user_id': user_id,
                    'is_pass': line.get('is_pass'),
                    'reason': line.get('reason'), 
                    'seq_no': seq_no,
                    'overall_remarks': activity_type_id.overall_remarks_approver
                }
                pcl_log = self.env['project.checklist.line.log'].create(data)
                
                for image in image_datas:
                    image_id = self.env['ir.attachment'].create(
                        {'datas': image, 'name': 'image'})
                    pcl_log.write({'image_ids': [(4, image_id.id)]})
                
                _logger.info(
                    "----checker-update--image_urls----,%s", image_urls)
                for url in image_urls:
                    _logger.info("----checker-update------,%s", url)
                    self.env['project.checklist.line.log.line'].create(
                        {'url': url, 'project_checklist_line_log_id': pcl_log.id})
        
        activity_type_id.sudo().button_set_to_checker(seq_no, user_id)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Approver Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)


    @restapi.method([(["/approver/checklist/update"], "POST")], auth="user")
    def update_checklist_approver(self):
        # approver will update the checklist and notification to admin
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        seq_no = False
        params = request.params
        user_id = False
        send_notification = False
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        if params.get('overall_remarks_approver'):
            activity_type_id.write(
                {'overall_remarks_approver': params.get('overall_remarks_approver')})
        seq_no = activity_type_id.seq_no

        if activity_type_id and user_id:
            activity_type_id.user_approver = user_id

        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                # checklist_id = self.env['project.checklist.line'].sudo().browse(int(line.get('line_id')))
                # if checklist_id:
                #     seq_no = checklist_id.activity_type_id.seq_no
                #     _logger.info("-----seq_no-------,%s",seq_no)
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})

                # if line.get('image_data'):
                #     for image_data in line.get('image_data'):
                #         attachment_vals_list = []
                #         attachment_vals_list.append(
                #             (0, 0, {'image': image_data}))
                #         # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                #         # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                #         checklist_id.write({'image_ids': attachment_vals_list})
                #         image_datas.append(image_data)

                # if line.get('image_data'):
                #     for image_data in line.get('image_data'):
                #         attachment_vals_list = []
                #         attachment_vals_list.append(
                #             (0, 0, {
                #                 'image': image_data.get('image'),
                #                 'img_desc': image_data.get('img_desc', False)  # Add img_desc
                #             }))
                #         checklist_id.write({'image_ids': attachment_vals_list})
                #         image_datas.append(image_data.get('image'))

                if line.get('image_data'):
                    attachment_vals_list = []
                    for image_data in line.get('image_data'):
                        image = image_data.get('image')
                        if image:  
                            # Fix padding if needed
                            missing_padding = len(image) % 4
                            if missing_padding:
                                image += '=' * (4 - missing_padding)

                            attachment_vals_list.append(
                                (0, 0, {
                                    'image': image,
                                    'img_desc': image_data.get('img_desc', False)
                                })
                            )
                            image_datas.append(image)

                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                if send_notification:
                    data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'approver', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                            'is_pass': line.get('is_pass'),
                            'reason': line.get('reason'), 'seq_no': seq_no,
                            'overall_remarks': activity_type_id.overall_remarks_approver}
                    pcl_log = self.env['project.checklist.line.log'].create(
                        data)
                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create(
                            {'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})
                    for url in image_urls:
                        _logger.info("----approver-update------,%s", url)
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

                # if line.get('image_data'):
                #     for image_data in line.get('image_data'):
                #         attachment_vals_list=[]
                #         attachment_vals_list.append((0,0,{'image': image_data}))
                #         # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                #         # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                #         checklist_id.write({'image_ids':attachment_vals_list})
        # submitting form and sending notification
        if send_notification:
            activity_type_id.sudo().button_approve(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/update/user/location"], "POST")], auth="user")
    def update_location_user(self):
        params = request.params
        if not params.get('lat'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send latitude'}),
                            content_type='application/json;charset=utf-8', status=201)
        if not params.get('long'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send longitude'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env.user.sudo().write({
            'lat': params.get('lat'),
            'longi': params.get('long'),

        })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Location Update'}),
                        content_type='application/json;charset=utf-8', status=200)
    # API FOR OFFLINE

    @restapi.method([(["/get/projects/offline"], "POST")], auth="user")
    def get_project_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        projects = self.env['project.info'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not projects:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Projects Not Found '}),
                            content_type='application/json;charset=utf-8', status=201)

        data = []
        for project in projects:
            image = ''
            if project.image:
                image = base64.b64encode(project.image).decode('utf-8')
            pdata = {'id': project.id, 'name': project.name, 'image': image}
            detail_line = []
            for line in project.project_details_line:
                image = ''
                if line.image:
                    image = base64.b64encode(line.image).decode('utf-8')
                detail_line.append(
                    {'id': line.id, 'name': line.name, 'image': image})
            pdata['details_line'] = detail_line
            data.append(pdata)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Data Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/offline"], "POST")], auth="user")
    def get_tower_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Towers Not Found '}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                tdata = {'id': tower.id, 'name': tower.name,
                         'project_id': project_id}
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    tdata['details_line_ids'] = detail_lines[0]
                    data.append(tdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/offline"], "POST")], auth="user")
    def get_floors_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        fdata = {'id': floor.id, 'name': floor.name, 'project_id': project_id,
                                 'tower_id': tower.id, 'details_line_ids': detail_lines[0]}

                        data.append(fdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Floors Data Fetch', 'floor_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/offline"], "POST")], auth="user")
    def get_flats_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        fdata = {'id': flat.id, 'name': flat.name, 'project_id': project_id,
                                 'tower_id': tower.id, 'details_line_ids': detail_lines[0]}
                        data.append(fdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flats Data Fetch', 'flat_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/activities/offline"], "POST")], auth="user")
    def get_floors_activities_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']
        project_activity_obj = self.env['project.activity']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            activity_data = {'id': activity.id, 'name': activity.name, 'project_id': project_id, 'tower_id': tower.id, 'floor_id': floor.id,
                                             'description': activity.description or '', 'write_date': str(activity.write_date), 'details_line_ids': detail_lines[0]}
                            data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity Data Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/activities/offline"], "POST")], auth="user")
    def get_flats_activities_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Flats Activity Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']
        project_activity_obj = self.env['project.activity']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            activity_data = {'id': activity.id, 'name': activity.name, 'project_id': project_id, 'tower_id': tower.id, 'flat_id': flat.id,
                                             'description': activity.description or '', 'write_date': str(activity.write_date), 'details_line_ids': detail_lines[0]}
                            data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flat Activity Data Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/activities/types/offline"], "POST")], auth="user")
    def get_floors_activities_types_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Activity Types Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                activity_data = {'id': activity_type.id, 'name': activity_type.name, 'activity_id': activity.id, 'project_id': project_id, 'tower_id': tower.id, 'floor_id': floor.id, 'write_date': str(
                                    activity.write_date), 'status': activity_type.status, 'progress': activity_type.progress_percentage, 'overall_remarks': activity_type.overall_remarks or '', 'details_line_ids': detail_lines[0]}
                                data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flat Activity Data Fetch', 'floors_activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/activities/types/offline"], "POST")], auth="user")
    def get_flats_activities_types_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Flats Activity Types Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                activity_data = {'id': activity_type.id, 'name': activity_type.name, 'activity_id': activity.id, 'project_id': project_id, 'tower_id': tower.id, 'flat_id': flat.id, 'write_date': str(
                                    activity.write_date), 'status': activity_type.status, 'progress': activity_type.progress_percentage, 'overall_remarks': activity_type.overall_remarks or '', 'details_line_ids': detail_lines[0]}
                                data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Floors Activity Data Fetch', 'flats_activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/checklist/offline"], "POST")], auth="user")
    def get_flats_checklist_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Checklist Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_checklist_line_log_obj = self.env['project.checklist.line.log']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                for checklist in activity_type.checklist_ids:
                                    image_data = []
                                    history = []
                                    log_lines = project_checklist_line_log_obj.search(
                                        [('line_id', '=', checklist.id)])

                                    for line in log_lines:
                                        base64image = []
                                        for irattachmnet in line.image_ids:
                                            base64image.append(
                                                irattachmnet.datas)
                                        history.append({
                                            'id': line.id,
                                            'name': line.checklist_template_id.name,
                                            'reason': line.reason,
                                            'is_pass': line.is_pass,
                                            'name': line.checklist_template_id.name,
                                            'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                                            'update_time': str(line.datetime),
                                            'base64image': base64image,
                                            'submitted': 'false',
                                        })
                                    # need to check checklist.id and checklist.template.id
                                    for image in checklist.image_ids:
                                        image_data.append(base64.b64encode(
                                            image.image).decode('utf-8'))
                                    checklist_data = {'history': history, 'activity_type_id': activity_type.id, 'id': checklist.id, 'name': checklist.checklist_template_id.name, 'activity_id': activity.id, 'project_id': project_id,
                                                      'tower_id': tower.id, 'flat_id': flat.id, 'write_date': str(activity.write_date), 'is_pass': checklist.is_pass, 'image': image_data, 'details_line_ids': detail_lines[0]}
                                    data.append(checklist_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flats Checklist Data Fetch', 'flats_checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/checklist/offline"], "POST")], auth="user")
    def get_floors_checklist_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Checklist Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_checklist_line_log_obj = self.env['project.checklist.line.log']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                for checklist in activity_type.checklist_ids:
                                    image_data = []
                                    history = []
                                    log_lines = project_checklist_line_log_obj.search(
                                        [('line_id', '=', checklist.id)])

                                    for line in log_lines:
                                        base64image = []
                                        for irattachmnet in line.image_ids:
                                            base64image.append(
                                                irattachmnet.datas)
                                        history.append({
                                            'id': line.id,
                                            'name': line.checklist_template_id.name,
                                            'reason': line.reason,
                                            'is_pass': line.is_pass,
                                            'name': line.checklist_template_id.name,
                                            'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                                            'update_time': str(line.datetime),
                                            'base64image': base64image,
                                            'submitted': 'false',
                                        })
                                    # need to check checklist.id and checklist.template.id
                                    for image in checklist.image_ids:
                                        image_data.append(base64.b64encode(
                                            image.image).decode('utf-8'))
                                    checklist_data = {'history': history, 'activity_type_id': activity_type.id, 'id': checklist.id, 'name': checklist.checklist_template_id.name, 'activity_id': activity.id, 'project_id': project_id,
                                                      'tower_id': tower.id, 'floor_id': floor.id, 'write_date': str(activity.write_date), 'is_pass': checklist.is_pass, 'image': image_data, 'details_line_ids': detail_lines[0]}
                                    data.append(checklist_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Floors Checklist Data Fetch', 'floors_checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/delete/activity"], "POST")], auth="user")
    def delete_activities(self):
        params = request.params
        # _logger.info("--create_duplicate_activities--params-1233333444-",params)
        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Id Not Found!'}),
                            content_type='application/json;charset=utf-8', status=400)

        actvity = request.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        actvity.activity_type_ids.unlink()
        actvity.unlink()

        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': ' Activity(s) Deleted'}),
            content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/duplicate/activities/create"], "POST")], auth="user")
    def create_duplicate_activities(self):
        params = request.params

        # _logger.info("--create_duplicate_activities--params-1233333444-",params)

        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Id Not Found!'}),
                            content_type='application/json;charset=utf-8', status=400)
        activity_id = request.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        if not activity_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity ID does not exist'}),
                            content_type='application/json;charset=utf-8', status=400)
        # Get the base name of the activity
        base_name = activity_id.name
        count = activity_id.count

        # _logger.info("--FLAT-121212-",activity_id.flat_id.name)
        # _logger.info("--FLOOR-1212121-",activity_id.floor_id.name)
        f_name = ''
        if activity_id.flat_id:
            for activity in activity_id.flat_id.activity_ids[-1]:
                activity_seq = int(activity.index_no) + 1
                f_name = activity_id.flat_id.name
                building_name = activity_id.flat_id.tower_id.name
                project = activity_id.flat_id.project_id.name

        if activity_id.floor_id:
            for activity in activity_id.floor_id.activity_ids[-1]:
                activity_seq = int(activity.index_no) + 1
                f_name = activity_id.floor_id.name
                building_name = activity_id.floor_id.tower_id.name
                project = activity_id.floor_id.project_id.name

        # Find the next available number suffix
        # duplicate_activities = request.env['project.activity'].sudo().search([('name', 'ilike', base_name)])
        # suffix = len(duplicate_activities)
        # Generate the name for the duplicate activity
        duplicate_name = f"{base_name}_{count}"
        vals = {
            "name": duplicate_name,
            "tower_id": activity_id.tower_id.id if activity_id.tower_id else False,
            "flat_id": activity_id.flat_id.id or False,
            "project_id": activity_id.project_id.id,
            "floor_id": activity_id.floor_id.id or False,
            "project_activity_name_id": activity_id.project_activity_name_id.id,
            "project_activity_id": activity_id.project_activity_id.id,
            "description": activity_id.description,
            # "progress_percentage": activity_id.progress_percentage,
            # "activity_type_ids": [(6, 0, activity_id.activity_type_ids.ids)]
        }
        # activity_type_re = project_activity_type_obj.create(project_activity_type_data)

        duplicate_activity_id = request.env['project.activity'].sudo().create(
            vals)

        for type_data in activity_id.activity_type_ids:
            data = {'activity_id': duplicate_activity_id.id, 'project_actn_id': type_data.project_actn_id.id, 'name': type_data.name, 'project_id': activity_id.project_id.id,
                    'tower_id': activity_id.tower_id.id or False, 'flat_id': activity_id.flat_id.id or False, 'floor_id': activity_id.floor_id.id or False}
            pat_rec = self.env['project.activity.type'].sudo().create(data)
            for checklist in type_data.checklist_ids:
                self.env['project.checklist.line'].sudo().create(
                    {'activity_type_id': pat_rec.id, 'checklist_template_id': checklist.checklist_template_id.id})

        ###
        activity_seq = '001'
        if duplicate_activity_id.name:
            # activity_name = duplicate_activity_id.name[:4].strip()
            activity_name = duplicate_activity_id.name

            duplicate_activity_id.index_no = activity_seq
            new_number = int(activity_seq) + 1
            # activity_seq = '{:03d}'.format(new_number)
            activity_type_seq = '001'
            for activity_type in duplicate_activity_id.activity_type_ids:
                no = 1 + 1
                temp = activity_type_seq
                activity_type.index_no = activity_type_seq
                new_number = int(activity_type_seq) + 1
                activity_type_seq = '{:03d}'.format(new_number)
                activity_type.seq_no = "VB"+"/" + str(project) + "/" + str(
                    building_name) + "/" + str(f_name) + "/" + str(activity_name) + "/" + str(temp)

        activity_id.count = count + 1
        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': f'Duplicate Activity ID {duplicate_activity_id.id} Created'}),
            content_type='application/json;charset=utf-8', status=200)

        # except Exception as e:
        #     _logger.error("An error occurred: %s", str(e))
        #     return Response(json.dumps({'status': 'FAILED', 'message': 'An error occurred'}),
        #                     content_type='application/json;charset=utf-8', status=500)


# Material Inspection


    @restapi.method([(["/maker/mi/update"], "POST")], auth="user")
    def update_mi_maker(self):
        # maker will update the checklist and click on submit button notification should sent to res. checker

        params = request.params
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        # _logger.info("---------update_checklist_maker---------,%s", params)

        if not params.get('mi_id') and not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env['material.inspection'].update_mi_maker(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/mi/reject"], "POST")], auth="user")
    def reject_mi_checker(self):
        # Checker reject the checklist , notification to maker
        params = request.params

        _logger.info("---------reject_mi_checker---------,%s", params)

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env['material.inspection'].sudo().reject_mi_checker(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checker Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/mi/update"], "POST")], auth="user")
    def update_mi_checker(self):
        # this method will get call from checekr to updte the checklist and submit. notification to approver
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        # activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        self.env['material.inspection'].sudo().update_mi_checker(params)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update', 'status': 'success'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/mi/reject"], "POST")], auth="user")
    def reject_mi_approver(self):
        # Approver will reject the checklist and go bakc to checker
        params = request.params
        # _logger.info("---------update_checklist_reject---------,%s", params)

        # _logger.info("---------update_checklist_checker---------,%s", params)
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].sudo().reject_mi_approver(params)

        # activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Approver Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/mi/update"], "POST")], auth="user")
    def update_mi_approver(self):
        # approver will update the checklist and notification to admin

        params = request.params

        # _logger.info("---------update_checklist_checker---------,%s", params)
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].sudo().update_mi_approver(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/material/inspection"], "POST")], auth="user")
    def get_material_inspection(self):
        # if params contain checked_by(id) will send realted MI data otherwise all MI data.
        response = {}
        params = request.params

        # if  not params.get('tower_id') or not params.get('mi_id'):
        #     return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Tower Id'}),
        #                     content_type='application/json;charset=utf-8', status=400)

        mi_data = self.env['material.inspection'].sudo().get_material_inspection(
            params.get('tower_id'), params.get('mi_id'))

        response['material_inspection'] = mi_data
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Data Fetch', 'mi_data': response}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/create/material/inspection"], "POST")], auth="user")
    def create_material_inspection(self):
        params = request.params
        # _logger.info("--create_duplicate_activities--params-1233333444-",params)
        if not params.get('project_info_id') and not params.get('tower_id') and not params.get('checked_by'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send project, tower id and Checked By(User) Id'}),
                            content_type='application/json;charset=utf-8', status=400)

        self.env['material.inspection'].sudo(
        ).create_material_inspection(params)

        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': 'Material Inspection Created'}),
            content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/towers"], "POST")], auth="user")
    def get_project_towers(self):
        params = request.params
        if not params.get('project_info_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Project Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        towers = self.env['project.tower'].sudo().get_project_towers(
            int(params.get('project_info_id')))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetch', 'towers': towers}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/mi/checklist"], "POST")], auth="user")
    def get_mi_checklist(self):
        checklist = self.env['mi.checklist'].sudo().get_mi_checklist()

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'MI Checklist Fetched', 'mi_checklist': checklist}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/delete/mi"], "POST")], auth="user")
    def delete_mi(self):
        params = request.params
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        mi_rec = self.env['material.inspection'].browse(
            int(params.get('mi_id'))).unlink()

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection form deleted'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/update/mi"], "POST")], auth="user")
    def update_mi(self):
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].update_mi(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Updated Successfully'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/replicate/mi"], "POST")], auth="user")
    def replicate_mi(self):
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        mi_id = params.get('mi_id')
        self.env['material.inspection'].replicate(int(mi_id))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Replicate Successfully'}),
                        content_type='application/json;charset=utf-8', status=200)

    # ForGot Password
    @restapi.method([(["/change_password"], "POST")], auth="user")
    def change_password(self):
        params = request.params

        if not params.get('user_id') and not params.get('old_password') and not params.get('new_password'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send User Id, Old Password and New password'}),
                            content_type='application/json;charset=utf-8', status=201)
        user_id = params.get('user_id')
        old_password = params.get('old_password')
        new_password = params.get('new_password')

        user = self.env['res.users'].sudo().browse(int(user_id))
        # if not user.check_password(old_password):
        #     return Response(json.dumps({'status': 'FAILED', 'message': 'Old password in incorrect'}),
        #             content_type='application/json;charset=utf-8', status=200)
        try:
            user.password = new_password
            return Response(json.dumps({'status': 'SUCCESS', 'message': 'password chnaged successfully'}),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as e:
            _logger.info("--change_password --e--", str(e))

            return Response(json.dumps({'status': 'FAILED', 'message': 'Can not change the password'}),
                            content_type='application/json;charset=utf-8', status=200)

    ### Training Report ###

    @restapi.method([(["/get/training/report"], "POST")], auth="user")
    def get_training_report_details(self):

        params = request.params
        response = {}
        traning_report = self.env['training.report'].sudo(
        ).get_training_report_details(params)
        # response['training_data'] = traning_report
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'tower_data': traning_report}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/create/training/report"], "POST")], auth="user")
    def create_training_report(self):

        params = request.params
        self.env['training.report'].sudo().create_training_report(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Training Report Created'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/towers"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):
        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        tower_records = self.env['project.tower'].sudo().search(
            [('project_id', '=', params.get('project_id'))])
        tower_data = [{'tower_id': tower.id, 'name': tower.name}
                      for tower in tower_records]

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'tower_data': tower_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # API for activity list: listing all the activities

    @restapi.method([(["/activities"], "POST")], auth="public")
    def get_activities(self):
        _logger.info("Fetching all activities")
        try:
            activities = request.env['project.activity.name'].sudo().search([])
            activity_list = [{'name': act.name,
                              'activity_id': act.id} for act in activities]
            # _logger.info("Successfully fetched activities: %s", activity_list)
            return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    # API for activity types {pre, post, during}

    @restapi.method([(["/activity/type_names"], "POST")], auth="public")
    def get_activity_type_names(self):
        _logger.info("Fetching activity type names")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            activity_id = data.get('activity_id')
            if not activity_id:
                _logger.warning("Activity ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity ID is required'}

            activity = request.env['project.activity.name'].sudo().browse(
                activity_id)
            if not activity.exists():
                _logger.warning("Activity not found for ID: %s", activity_id)
                return {'status': 'FAILED', 'message': 'Activity not found'}

            activity_type_lines = request.env['project.activity.name.line'].sudo().search([
                ('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_type_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    # API for specific checklines associated to activity and its types

    @restapi.method([(["/activity/checklist"], "POST")], auth="public")
    def get_activity_checklist(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                _logger.warning(
                    "Activity Type Name ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity Type Name ID is required'}

            activity_type_name = request.env['project.activity.name.line'].sudo().browse(
                patn_id)
            if not activity_type_name.exists():
                _logger.warning(
                    "Activity Type Name not found for ID: %s", patn_id)
                return {'status': 'FAILED', 'message': 'Activity Type Name not found'}

            checklists = request.env['project.activity.type.name.line'].sudo().search([
                ('patn_id', '=', patn_id)])
            checklist_items = [{'name': chk.checklist_id.name,
                                'id': chk.checklist_id.id} for chk in checklists]

            _logger.info("Successfully fetched checklist items: %s",
                         checklist_items)
            return {'status': 'SUCCESS', 'message': 'Checklist items fetched successfully', 'data': checklist_items}
        except Exception as e:
            _logger.exception("Error fetching checklist items: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching checklist items', 'error': str(e)}


#  for set flag manually
# for projects

    @restapi.method([(["/api/project/info"], "POST")], auth="user")
    def get_project_infolist(self):
        _logger.info("Fetching all projects")

        # try:
        #     projects = request.env['project.info'].sudo().search([])
        #     project_data = [{'project_id': project.id,
        #                      'project_name': project.name} for project in projects]

        #     _logger.info("-----projects------%s", project_data)
        #     return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'projects': project_data}

        # except Exception as e:
        #     _logger.exception("Error fetching activities: %s", str(e))
        #     return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

        project_ids = self.env['project.info'].sudo().search(
            [('assigned_to_ids', 'in', self.env.user.id)])
        project_data = []
        get_param = self.env['ir.config_parameter'].sudo().get_param
        for project in project_ids:
            project_data.append({
                'project_name': project.name,
                'project_id': project.id,
            })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'projects': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # @restapi.method([(["/api/tower/info"], "POST")], auth="public")
    # def get_tower_info(self):
    #     try:
    #         # Parse JSON payload
    #         data = json.loads(request.httprequest.data.decode('utf-8'))
    #         _logger.info("Received request data: %s", data)

    #         # Extract project_id
    #         project_id = data.get('project_id')

    #         # Validate project_id
    #         if not project_id:
    #             _logger.warning("Project ID is missing in the request")
    #             return {'status': 'FAILED', 'message': 'Please send Project ID'}

    #         # Fetch tower records based on project_id
    #         tower_records = request.env['project.tower'].sudo().search(
    #             [('project_id', '=', project_id)])
    #         tower_data = [{'tower_id': tower.id, 'tower_name': tower.name}
    #                       for tower in tower_records]

    #         # Log fetched data
    #         # _logger.info("Fetched tower data: %s", tower_data)

    #         # Return success response
    #         return {'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'towers': tower_data}

    #     except Exception as e:
    #         _logger.exception("Unexpected error occurred")
    #         return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    @restapi.method([(["/api/tower/info"], "POST")], auth="public")
    def get_tower_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            # Extract project_id
            project_id = data.get('project_id')

            # Validate project_id
            if not project_id:
                _logger.warning("Project ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Project ID'}

            # ✅ Fetch tower records from project_info_tower_line_temp
            tower_records = request.env['project.info.tower.line.temp'].sudo().search(
                [('project_id', '=', project_id)]
            )

            # Prepare tower data
            tower_data = [
                {
                    'tower_id': tower.id,
                    'tower_name': tower.name or ''
                }
                for tower in tower_records
            ]

            # Return success response
            return {
                'status': 'SUCCESS',
                'message': 'Tower Data Fetched',
                'towers': tower_data
            }

        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {
                'status': 'FAILED',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }
    
    @restapi.method([(["/api/floor/info"], "POST")], auth="public")
    def get_floor_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            tower_temp_id = data.get('tower_id')

            if not tower_temp_id:
                _logger.warning("Tower ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Tower ID'}

            # ✅ Find the temp tower
            temp_tower = request.env['project.info.tower.line.temp'].sudo().browse(tower_temp_id)
            if not temp_tower.exists():
                return {'status': 'FAILED', 'message': 'Invalid Temporary Tower ID'}

            # ✅ Find matching tower in main project.tower model
            real_tower = request.env['project.tower'].sudo().search(
                [('name', '=', temp_tower.name)], limit=1
            )

            if not real_tower:
                return {'status': 'FAILED', 'message': 'Matching Tower not found in main tower list'}

            # ✅ Fetch all floors of that real tower
            floor_records = request.env['project.floors'].sudo().search(
                [('tower_id', '=', real_tower.id)]
            )

            floor_data = [
                {'floor_id': floor.id, 'floor_name': floor.name or ''}
                for floor in floor_records
            ]

            return {
                'status': 'SUCCESS',
                'message': 'Floor Data Fetched',
                'floors': floor_data
            }

        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {
                'status': 'FAILED',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }

    
 
    # @restapi.method([(["/api/floor/info"], "POST")], auth="public")
    # def get_floor_info(self):
    #     try:
    #         # Parse JSON payload
    #         data = json.loads(request.httprequest.data.decode('utf-8'))
    #         _logger.info("Received request data: %s", data)

    #         # Extract project_id
    #         tower_id = data.get('tower_id')

    #         # Validate project_id
    #         if not tower_id:
    #             _logger.warning("Tower ID is missing in the request")
    #             return {'status': 'FAILED', 'message': 'Please send Tower ID'}

    #         # Fetch tower records based on project_id
    #         floor_records = request.env['project.floors'].sudo().search(
    #             [('tower_id', '=', tower_id)])
    #         floor_data = [{'floor_id': floor.id, 'floor_name': floor.name}
    #                       for floor in floor_records]

    #         # Log fetched data
    #         # _logger.info("Fetched Floor data: %s", floor_data)

    #         # Return success response
    #         return {'status': 'SUCCESS', 'message': 'Floor Data Fetched', 'floors': floor_data}
    #     except Exception as e:
    #         _logger.exception("Unexpected error occurred")
    #         return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    # @restapi.method([(["/api/flat/info"], "POST")], auth="public")
    # def get_flat_info(self):
    #     try:
    #         # Parse JSON payload
    #         data = json.loads(request.httprequest.data.decode('utf-8'))
    #         _logger.info("Received request data: %s", data)

    #         # Extract project_id
    #         tower_id = data.get('tower_id')

    #         # Validate project_id
    #         if not tower_id:
    #             _logger.warning("Tower ID is missing in the request")
    #             return {'status': 'FAILED', 'message': 'Please send Tower ID'}

    #         # Fetch tower records based on project_id
    #         flat_records = request.env['project.flats'].sudo().search(
    #             [('tower_id', '=', tower_id)])
    #         flat_data = [{'flat_id': flat.id, 'flat_name': flat.name}
    #                      for flat in flat_records]

    #         # Log fetched data
    #         _logger.info("Fetched Flat data: %s", flat_data)

    #         # Return success response
    #         return {'status': 'SUCCESS', 'message': 'Floor Data Fetched', 'flats': flat_data}
    #     except Exception as e:
    #         _logger.exception("Unexpected error occurred")
    #         return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    @restapi.method([(["/api/flat/info"], "POST")], auth="public")
    def get_flat_info(self):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            tower_temp_id = data.get('tower_id')

            if not tower_temp_id:
                _logger.warning("Tower ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Tower ID'}

            # ✅ Find the temp tower
            temp_tower = request.env['project.info.tower.line.temp'].sudo().browse(tower_temp_id)
            if not temp_tower.exists():
                return {'status': 'FAILED', 'message': 'Invalid Temporary Tower ID'}

            # ✅ Find matching tower in project.tower model
            real_tower = request.env['project.tower'].sudo().search(
                [('name', '=', temp_tower.name)], limit=1
            )

            if not real_tower:
                return {'status': 'FAILED', 'message': 'Matching Tower not found in main tower list'}

            # ✅ Fetch flats linked to that real tower
            flat_records = request.env['project.flats'].sudo().search(
                [('tower_id', '=', real_tower.id)]
            )

            flat_data = [
                {
                    'flat_id': flat.id,
                    'flat_name': flat.name or '',
                    'floor_id': flat.floor_id.id if flat.floor_id else '',
                    'floor_name': flat.floor_id.name if flat.floor_id else ''
                }
                for flat in flat_records
            ]

            return {
                'status': 'SUCCESS',
                'message': 'Flat Data Fetched',
                'flats': flat_data
            }

        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {
                'status': 'FAILED',
                'message': 'An unexpected error occurred',
                'error': str(e)
            }



    @restapi.method([(["/api/users/list"], "POST")], auth="public")
    def get_project_responsibles(self):
        try:
            group = request.env.ref(
            "custom_project_management.group_quality_maker")
            # Fetch all partners
            partners = request.env['res.users'].sudo().search([
            ('groups_id', 'in', group.id)
        ])
            # Prepare the partner data for response
            partner_data = [
                {'id': partner.id, 'name': partner.name, }
                for partner in partners
            ]

            # _logger.info("Fetched project responsible users: %s", partner_data)

            # Return the response
            return {
                'status': 'SUCCESS',
                'message': 'Project responsibles fetched successfully',
                'responsibles': partner_data   
            }

        except Exception as e:
            _logger.exception(
                "Error fetching project responsibles: %s", str(e))
            return {
                'status': 'FAILED',
                'message': 'An error occurred while fetching project responsibles',
                'error': str(e)
            }

    @restapi.method([(["/api/activities/info"], "POST")], auth="public")
    def get_nc_activities(self):
        _logger.info("Fetching all activities")
        try:
            activities = request.env['project.activity.name'].sudo().search([])
            activity_list = [{'name': act.name,
                              'activity_id': act.id} for act in activities]
            # _logger.info("Successfully fetched activities: %s", activity_list)
            return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    @restapi.method([(["/api/activity/type/info"], "POST")], auth="public")
    def get_nc_activity_type_names(self):
        _logger.info("Fetching activity type names")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            activity_id = data.get('activity_id')
            if not activity_id:
                _logger.warning("Activity ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity ID is required'}

            activity = request.env['project.activity.name'].sudo().browse(
                activity_id)
            if not activity.exists():
                _logger.warning("Activity not found for ID: %s", activity_id)
                return {'status': 'FAILED', 'message': 'Activity not found'}

            activity_type_lines = request.env['project.activity.name.line'].sudo().search([
                ('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_type_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    @restapi.method([(["/api/activity/checklist/info"], "POST")], auth="public")
    def get_nc_activity_checklist(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                _logger.warning(
                    "Activity Type Name ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity Type Name ID is required'}

            activity_type_name = request.env['project.activity.name.line'].sudo().browse(
                patn_id)
            if not activity_type_name.exists():
                _logger.warning(
                    "Activity Type Name not found for ID: %s", patn_id)
                return {'status': 'FAILED', 'message': 'Activity Type Name not found'}

            checklists = request.env['project.activity.type.name.line'].sudo().search([
                ('patn_id', '=', patn_id)])
            checklist_items = [{'name': chk.checklist_id.name,
                                'id': chk.checklist_id.id} for chk in checklists]

            _logger.info("Successfully fetched checklist items: %s",
                         checklist_items)
            return {'status': 'SUCCESS', 'message': 'Checklist items fetched successfully', 'data': checklist_items}
        except Exception as e:
            _logger.exception("Error fetching checklist items: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching checklist items', 'error': str(e)}

    # @restapi.method([(["/api/activities/info"], "POST")], auth="public")
    # def get_activities_info(self):
    #     _logger.info("Fetching all activities")
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("Received request data: %s", data)

    #         # Extract project_id
    #         floor_id = data.get('floor_id')
    #         flat_id = data.get('flat_id')
    #         tower_id = data.get('tower_id')
    #         project_id = data.get('project_id')

    #         domain = []

    #         if floor_id:
    #             domain.append(('floor_id', '=', floor_id))
    #         if flat_id:
    #             domain.append(('flat_id', '=', flat_id))
    #         if tower_id:
    #             domain.append(('tower_id', '=', tower_id))
    #         if project_id:
    #             domain.append(('project_id', '=', project_id))

    #         _logger.info("Search domain for activities: %s", domain)

    #         activities = request.env['project.activity.name'].sudo().search(
    #             domain)
    #         activity_list = [{'name': act.name,
    #                           'activity_id': act.id} for act in activities]
    #         # _logger.info("Successfully fetched activities: %s", activity_list)
    #         return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
    #     except Exception as e:
    #         _logger.exception("Error fetching activities: %s", str(e))
    #         return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    # def get_activities_info(self):
    #     _logger.info("Fetching all activities")
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("Received request data: %s", data)

    #         # Extract project_id
    #         floor_id = data.get('floor_id')
    #         flat_id = data.get('flat_id')
    #         tower_id = data.get('tower_id')
    #         project_id = data.get('project_id')

    #         domain = []

    #         if floor_id:
    #             domain.append(('floor_id', '=', floor_id))
    #         if flat_id:
    #             domain.append(('flat_id', '=', flat_id))
    #         if tower_id:
    #             domain.append(('tower_id', '=', tower_id))
    #         if project_id:
    #             domain.append(('project_id', '=', project_id))

    #         _logger.info("Search domain for activities: %s", domain)

    #         activity_ids = request.env['project.activity'].sudo().search(
    #             domain).mapped('project_activity_name_id')
    #         activities = request.env['project.activity.name'].sudo().search(
    #             [('id', 'in', activity_ids.ids)])
    #         activity_list = [{'name': act.name,
    #                           'activity_id': act.id} for act in activities]
    #         # _logger.info("Successfully fetched activities: %s", activity_list)
    #         return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
    #     except Exception as e:
    #         _logger.exception("Error fetching activities: %s", str(e))
    #         return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    # API for activity types {pre, post, during}

    # @restapi.method([(["/api/activity/type/info"], "POST")], auth="public")
    # def get_activity_type_info(self):
    #     _logger.info("Fetching activity type names")
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("Received data: %s", data)

    #         activity_id = data.get('activity_id')
    #         if not activity_id:
    #             _logger.warning("Activity ID is missing in the request")
    #             return {'status': 'FAILED', 'message': 'Activity ID is required'}

    #         activity = request.env['project.activity.name'].sudo().browse(
    #             activity_id)
    #         if not activity.exists():
    #             _logger.warning("Activity not found for ID: %s", activity_id)
    #             return {'status': 'FAILED', 'message': 'Activity not found'}

    #         # Fetch activity type names associated with the given activity
    #         activity_lines = request.env['project.activity.name.line'].sudo().search(
    #             [('pan_id', '=', activity_id)])
    #         activity_type_names = [
    #             {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_lines]

    #         _logger.info("Successfully fetched activity type names: %s",
    #                      activity_type_names)
    #         return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
    #     except Exception as e:
    #         _logger.exception("Error fetching activity type names: %s", str(e))
    #         return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    # # API for specific checklines associated to activity and its types

    # @restapi.method([(["/api/activity/checklist/info"], "POST")], auth="public")
    # def get_activity_checklist_info(self):
    #     _logger.info(
    #         "📥 [Checklist Info API] Request received to fetch checklist items for specific activity type name line")
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info(
    #             "📦 [Checklist Info API] Received data payload: %s", data)

    #         patn_id = data.get('patn_id')
    #         if not patn_id:
    #             _logger.warning(
    #                 "⚠️ [Checklist Info API] Missing 'patn_id' in request data")
    #             return {'status': 'FAILED', 'message': 'Activity Name Line ID is required'}

    #         # Fetch the project.activity.name.line record
    #         activity_name_line = request.env['project.activity.name.line'].sudo().browse(
    #             patn_id)
    #         if not activity_name_line.exists():
    #             _logger.warning(
    #                 "❌ [Checklist Info API] No activity name line found for patn_id: %s", patn_id)
    #             return {'status': 'FAILED', 'message': 'Activity Name Line not found'}

    #         _logger.info("✅ [Checklist Info API] Found activity name line: %s (ID: %s)",
    #                      activity_name_line.name, activity_name_line.id)

    #         # Fetch the related activity type (project.activity.type.name)
    #         activity_type = activity_name_line.patn_id
    #         if not activity_type:
    #             _logger.warning(
    #                 "❌ [Checklist Info API] No related activity type found for line ID: %s", patn_id)
    #             return {'status': 'FAILED', 'message': 'Related Activity Type not found'}

    #         _logger.info("🔗 [Checklist Info API] Linked to activity type: %s (ID: %s)",
    #                      activity_type.name, activity_type.id)

    #         # Fetch checklist items from project.activity.type.name.line using patn_id
    #         checklists = request.env['project.activity.type.name.line'].sudo().search([
    #             ('patn_id', '=', activity_type.id)
    #         ])
    #         _logger.info("📋 [Checklist Info API] Fetched %s checklist lines for patn_id: %s", len(
    #             checklists), activity_type.id)

    #         checklist_items = [{'name': chk.checklist_id.name,
    #                             'id': chk.checklist_id.id} for chk in checklists]
    #         _logger.debug(
    #             "📝 [Checklist Info API] Final checklist items: %s", checklist_items)

    #         return {
    #             'status': 'SUCCESS',
    #             'message': 'Checklist items fetched successfully',
    #             'data': checklist_items
    #         }

    #     except Exception as e:
    #         _logger.exception(
    #             "💥 [Checklist Info API] Error occurred while fetching checklist items: %s", str(e))
    #         return {
    #             'status': 'FAILED',
    #             'message': 'Error fetching checklist items',
    #             'error': str(e)
    #         }

    # @restapi.method([(["/api/nc/create"], "POST")], auth="public")
    # def create_nc(self):
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("POST API for NC creation called")
    #         _logger.info("Received JSON request: %s", data)
    #         _logger.info("Extracted activity_id: %s", data.get('activity_id'))

    #         project_info_id = int(data.get('project_id')) if data.get(
    #             'project_id') else None
    #         project_tower_id = int(data.get('tower_id')) if data.get(
    #             'tower_id') else None
    #         project_floor_id = int(data.get('floor_id')) if data.get(
    #             'floor_id') else None
    #         project_flats_id = int(data.get('flat_id')) if data.get(
    #             'flat_id') else None
    #         project_activity_id = int(data.get('activity_id')) if data.get(
    #             'activity_id') else None
    #         project_act_type = int(data.get('activity_type_id')) if data.get(
    #             'activity_type_id') else None
    #         project_check_line = int(
    #             data.get('id')) if data.get('id') else None
    #         project_responsible = int(data.get('project_responsible_id')) if data.get(
    #             'project_responsible_id') else None
    #         # Extract required fields
    #         # project_info_id = data.get('project_id')
    #         # project_tower_id = data.get('tower_id')
    #         # project_floor_id = data.get('floor_id')
    #         # project_flats_id = data.get('flat_id')
    #         # project_activity_id = data.get('activity_id')
    #         # _logger.info("Extracted activity_id: %s", project_activity_id)

    #         # project_act_type_id = data.get('activity_type_id')
    #         # # project_check_line_id = data.get('id')
    #         # # _logger.info("================== actual id=============%s",
    #         # #              project_check_line_id)
    #         # project_check_line = data.get('id')

    #         # Get the correct project_check_line_id by finding the record with this checklist_id
    #         checklist_template_id = int(
    #             project_check_line) if project_check_line else None

    #         # Search the correct project.activity.type.name.line
    #         project_check_line_record = request.env['project.activity.type.name.line'].sudo().search([
    #             ('checklist_id', '=', checklist_template_id)
    #         ], limit=1)

    #         project_check_line_id = project_check_line_record.id if project_check_line_record else None

    #         activity_type_id = int(
    #             project_act_type) if project_act_type else None

    #         # Search the correct project.activity.name.line
    #         activity_type_record = request.env['project.activity.name.line'].sudo().search([
    #             ('patn_id', '=', activity_type_id)
    #         ], limit=1)

    #         project_act_type_id = activity_type_record.id if activity_type_record else None

    #         # _logger.info("Extracted checklist_id: %s",
    #         #              project_check_line_id.id.checklist_id.name)
    #         # int(data.get('flat_id')) if data.get( 'flat_id') else None
    #         custom_checklist_item = data.get('custom_checklist_item')
    #         description = data.get('description')
    #         rectified_image = data.get('rectified_image')
    #         flag_category = data.get('flag_category')
    #         project_create_date = data.get('project_create_date')
    #         project_responsible = data.get('project_responsible_id')
    #         status = data.get('status')

    #         # Handle Image Upload

    #         image_data = None
    #         rectified_image_data = rectified_image

    #         if rectified_image_data:
    #             try:
    #                 image_data = rectified_image_data.split(',')[1]
    #                 decoded_image = base64.b64decode(image_data)

    #                 attachment = self.env['ir.attachment'].sudo().create({
    #                     'name': 'rectified_image.jpg',
    #                     'type': 'binary',
    #                     'datas': base64.b64encode(decoded_image),
    #                     'res_model': 'manually.set.flag',
    #                     'res_id': nc.id,
    #                 })
    #             except Exception as e:
    #                 _logger.error(f"Error decoding image: {str(e)}")

    #         # Create NC record
    #         nc_values = {
    #             'project_info_id': project_info_id,
    #             'project_tower_id': project_tower_id,
    #             'project_floor_id': project_floor_id,
    #             'project_flats_id': project_flats_id,
    #             'project_activity_id': project_activity_id,
    #             'project_act_type_id': project_act_type_id,
    #             'project_check_line_id': project_check_line_id,
    #             'description': description,
    #             'rectified_image': image_data,
    #             'flag_category': flag_category,
    #             'project_create_date': project_create_date,
    #             'project_responsible': project_responsible,
    #             'status': status,
    #         }
    #         _logger.info(
    #             "====================nc_values===============%s", nc_values)
    #         if custom_checklist_item:
    #             nc_values['custom_checklist_item'] = custom_checklist_item

    #         nc_values.pop('seq_number', None)
    #         nc_values['seq_number'] = request.env['ir.sequence'].sudo(
    #         ).next_by_code('manually.set.flag') or _('New')  # type: ignore

    #         nc = request.env['manually.set.flag'].sudo().create(nc_values)
    #         _logger.info("NC created successfully with ID: %s", nc.id)

    #         # Prepare response data
    #         response_data = {
    #             'status': 'success',
    #             'nc_id': nc.id,
    #             'message': 'NC created successfully.',
    #             'nc_data': {
    #                 'seq_no': nc.seq_number,
    #                 'project_id': nc.project_info_id.id,
    #                 'tower_id': nc.project_tower_id.id,
    #                 'floor_id': nc.project_floor_id.id,
    #                 'flat_id': nc.project_flats_id.id,
    #                 'activity_id': nc.project_activity_id.id,
    #                 'activity_type_id': nc.project_act_type_id.id,
    #                 'id': nc.project_check_line_id.id,
    #                 'description': nc.description,
    #                 'flag_category': nc.flag_category,
    #                 'rectified_image': rectified_image,
    #                 'project_create_date': nc.project_create_date,
    #                 'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
    #                 'custom_checklist': nc.custom_checklist_item
    #             }
    #         }
    #         _logger.info("=======responseee========%s", response_data)
    #         # Send Notification to Project Responsible
    #         if nc.project_responsible:
    #             notification_status = self.send_notification(nc)
    #             response_data['notification_status'] = notification_status

    #         return response_data, 201  # HTTP 201 Created

    #     except Exception as e:
    #         _logger.error("Error creating NC: %s", e)
    #         return {
    #             'status': 'error',
    #             'message': f'Failed to create NC: {str(e)}'
    #         }, 500  # HTTP 500 Internal Server Error

    # def send_notification(self, nc):
    #     """ Sends push notification to the responsible person """
    #     if not nc.project_responsible:
    #         return {'error': 'No responsible person assigned'}

    #     project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
    #     tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
    #     flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
    #     flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
    #     floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

    #     # Conditional address logic
    #     if flat_name:
    #         location_detail = f"Flat/{flat_name}"
    #     elif floor_name:
    #         location_detail = f"Floor/{floor_name}"
    #     else:
    #         location_detail = ""

    #     seq_no = nc.seq_number
    #     # Get current user's name
    #     current_user_name = request.env.user.name if request.env.user else 'Unknown User'

    #     # Update the message
    #     message = f"{current_user_name} has created a {flag_category} for {project_name}/{tower_name}"
    #     if location_detail:
    #         message += f"/{location_detail}"
    #         message += "."
    #     title = message

    #     # Get Push Notification ID
    #     player_id, user_r = request.env['res.users'].sudo(
    #     ).get_player_id(nc.project_responsible.id)
    #     player_ids = [player_id] if player_id else []

    #     if not player_ids:
    #         return {'error': 'No push notification ID found for the responsible person'}

    #     # OneSignal API credentials
    #     app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
    #     rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

    #     # Data to send in the notification
    #     data = {
    #         "app_id": app_id,
    #         "include_player_ids": player_ids,
    #         "contents": {"en": message},
    #         "headings": {"en": title},
    #     }

    #     # Convert data to JSON
    #     data_json = json.dumps(data)

    #     # URL for OneSignal REST API
    #     url = "https://onesignal.com/api/v1/notifications"

    #     # Headers for the request
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Basic {rest_api_key}"
    #     }

    #     # Send the notification
    #     response = requests.post(url, data=data_json, headers=headers)

    #     # Log Notification Status
    #     status = 'sent' if response.status_code == 200 else 'failed'
    #     request.env[''].sudo().create({
    #         'title': title if status == 'sent' else f"{title} (Failed)",
    #         'message': message,
    #         'res_user_id': nc.project_responsible.id,
    #         'player_id': player_id,
    #         'seq_no': seq_no,
    #         'status': status,
    #         'table_id': nc.id,
    #         'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
    #         'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
    #     })

    #     return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}

    
    # @restapi.method([(["/api/nc/create"], "POST")], auth="public")
    # def create_nc(self):
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("POST API for NC creation called")
    #         _logger.info("Received JSON request: %s", data)
    #         _logger.info("Extracted activity_id: %s", data.get('activity_id'))

    #         # Extract and convert IDs
    #         project_info_id = int(data.get('project_id')) if data.get('project_id') else None
    #         project_tower_id = int(data.get('tower_id')) if data.get('tower_id') else None
    #         project_floor_id = int(data.get('floor_id')) if data.get('floor_id') else None
    #         project_flats_id = int(data.get('flat_id')) if data.get('flat_id') else None
    #         project_activity_id = int(data.get('activity_id')) if data.get('activity_id') else None
    #         project_act_type = int(data.get('activity_type_id')) if data.get('activity_type_id') else None
    #         project_check_line = int(data.get('id')) if data.get('id') else None
    #         project_responsible = int(data.get('project_responsible_id')) if data.get('project_responsible_id') else None

    #         # Get the correct project_check_line_id by finding the record with this checklist_id
    #         checklist_template_id = int(project_check_line) if project_check_line else None

    #         # Search the correct project.activity.type.name.line
    #         project_check_line_record = request.env['project.activity.type.name.line'].sudo().search([
    #             ('checklist_id', '=', checklist_template_id)
    #         ], limit=1)

    #         project_check_line_id = project_check_line_record.id if project_check_line_record else None

    #         activity_type_id = int(project_act_type) if project_act_type else None

    #         # Search the correct project.activity.name.line
    #         activity_type_record = request.env['project.activity.name.line'].sudo().search([
    #             ('patn_id', '=', activity_type_id)
    #         ], limit=1)

    #         project_act_type_id = activity_type_record.id if activity_type_record else None

    #         # Extract other fields
    #         custom_checklist_item = data.get('custom_checklist_item')
    #         description = data.get('description')
    #         rectified_image_data = data.get('rectified_image')
    #         flag_category = data.get('flag_category')
    #         project_create_date = data.get('project_create_date')
    #         status = data.get('status')

    #         # Handle Image Data - Extract base64 string BEFORE creating NC
    #         image_data = None
    #         if rectified_image_data:
    #             try:
    #                 # Extract base64 data (remove data:image/jpeg;base64, prefix if present)
    #                 if ',' in rectified_image_data:
    #                     image_data = rectified_image_data.split(',')[1]
    #                 else:
    #                     image_data = rectified_image_data
    #                 _logger.info("Image data extracted successfully")
    #             except Exception as e:
    #                 _logger.error(f"Error extracting image data: {str(e)}")

    #         # Prepare NC values
    #         nc_values = {
    #             'project_info_id': project_info_id,
    #             'project_tower_id': project_tower_id,
    #             'project_floor_id': project_floor_id,
    #             'project_flats_id': project_flats_id,
    #             'project_activity_id': project_activity_id,
    #             'project_act_type_id': project_act_type_id,
    #             'project_check_line_id': project_check_line_id,
    #             'description': description,
    #             'rectified_image': image_data,
    #             'flag_category': flag_category,
    #             'project_create_date': project_create_date,
    #             'project_responsible': project_responsible,
    #             'status': status,
    #         }

    #         # Add custom checklist item if provided
    #         if custom_checklist_item:
    #             nc_values['custom_checklist_item'] = custom_checklist_item

    #         # Generate sequence number
    #         nc_values['seq_number'] = request.env['ir.sequence'].sudo().next_by_code('manually.set.flag') or 'New'
    #         _logger.info("NC values prepared: %s", nc_values)

    #         # Create NC record
    #         nc = request.env['manually.set.flag'].sudo().create(nc_values)
    #         _logger.info("NC created successfully with ID: %s", nc.id)

    #         # Create attachment AFTER nc record is created
    #         if rectified_image_data and image_data:
    #             try:
    #                 decoded_image = base64.b64decode(image_data)
    #                 attachment = request.env['ir.attachment'].sudo().create({
    #                     'name': f'rectified_image_{nc.seq_number}.jpg',
    #                     'type': 'binary',
    #                     'datas': base64.b64encode(decoded_image),
    #                     'res_model': 'manually.set.flag',
    #                     'res_id': nc.id,
    #                 })
    #                 _logger.info("Attachment created successfully with ID: %s", attachment.id)
    #             except Exception as e:
    #                 _logger.error(f"Error creating attachment: {str(e)}")

    #         # Prepare response data
    #         response_data = {
    #             'status': 'success',
    #             'nc_id': nc.id,
    #             'message': 'NC created successfully.',
    #             'nc_data': {
    #                 'seq_no': nc.seq_number,
    #                 'project_id': nc.project_info_id.id if nc.project_info_id else None,
    #                 'tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
    #                 'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
    #                 'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
    #                 'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
    #                 'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
    #                 'id': nc.project_check_line_id.id if nc.project_check_line_id else None,
    #                 'description': nc.description,
    #                 'flag_category': nc.flag_category,
    #                 'rectified_image': rectified_image_data,
    #                 'project_create_date': nc.project_create_date,
    #                 'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
    #                 'custom_checklist': nc.custom_checklist_item
    #             }
    #         }
    #         _logger.info("Response prepared: %s", response_data)

    #         # Send Notification to Project Responsible
    #         if nc.project_responsible:
    #             try:
    #                 notification_status = self.send_notification(nc)
    #                 response_data['notification_status'] = notification_status
    #             except Exception as e:
    #                 _logger.error(f"Error sending notification: {str(e)}")
    #                 response_data['notification_status'] = {'error': f'Failed to send notification: {str(e)}'}

    #         return response_data  # HTTP 201 Created

    #     except Exception as e:
    #         _logger.error("Error creating NC: %s", str(e))
    #         _logger.exception("Full traceback:")
    #         return {
    #             'status': 'error',
    #             'message': f'Failed to create NC: {str(e)}'
    #         }, 500  # HTTP 500 Internal Server Error


    # @restapi.method([(["/api/nc/create"], "POST")], auth="public")
    # def create_nc(self):
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("POST API for NC creation called")
    #         _logger.info("Received JSON request: %s", data)

    #         # Extract incoming IDs (some may come from temp models)
    #         project_info_id = int(data.get('project_id')) if data.get('project_id') else None
    #         temp_tower_id = int(data.get('tower_id')) if data.get('tower_id') else None
    #         project_floor_id = int(data.get('floor_id')) if data.get('floor_id') else None
    #         project_flats_id = int(data.get('flat_id')) if data.get('flat_id') else None
    #         project_activity_id = int(data.get('activity_id')) if data.get('activity_id') else None
    #         project_act_type = int(data.get('activity_type_id')) if data.get('activity_type_id') else None
    #         project_check_line = int(data.get('id')) if data.get('id') else None
    #         project_responsible = int(data.get('project_responsible_id')) if data.get('project_responsible_id') else None

    #         # -------------------------------------------
    #         # 🔍 Resolve actual Tower ID from temp model
    #         # -------------------------------------------
    #         project_tower_id = None
    #         if temp_tower_id:
    #             tower_temp = request.env['project.info.tower.line.temp'].sudo().browse(temp_tower_id)
    #             if tower_temp and tower_temp.tower_id:
    #                 project_tower_id = tower_temp.tower_id.id
    #                 _logger.info(f"Resolved real Tower ID: {project_tower_id} from temp ID: {temp_tower_id}")
    #             else:
    #                 _logger.warning(f"No matching project.tower found for temp tower ID: {temp_tower_id}")
    #         else:
    #             _logger.warning("tower_id not provided or invalid in payload")

    #         # -------------------------------------------
    #         # Lookup checklist & activity type records
    #         # -------------------------------------------
    #         checklist_template_id = int(project_check_line) if project_check_line else None
    #         project_check_line_record = request.env['project.activity.type.name.line'].sudo().search([
    #             ('checklist_id', '=', checklist_template_id)
    #         ], limit=1)
    #         project_check_line_id = project_check_line_record.id if project_check_line_record else None

    #         activity_type_record = request.env['project.activity.name.line'].sudo().search([
    #             ('patn_id', '=', project_act_type)
    #         ], limit=1)
    #         project_act_type_id = activity_type_record.id if activity_type_record else None

    #         # Extract main data
    #         custom_checklist_item = data.get('custom_checklist_item')
    #         description = data.get('description')
    #         flag_category = data.get('flag_category')
    #         project_create_date = data.get('project_create_date')
    #         status = data.get('status')

    #         # -------------------------------------------
    #         # Prepare NC record
    #         # -------------------------------------------
    #         nc_values = {
    #             'project_info_id': project_info_id,
    #             'project_tower_id': project_tower_id,   # ✅ Real tower ID
    #             'project_floor_id': project_floor_id,
    #             'project_flats_id': project_flats_id,
    #             'project_activity_id': project_activity_id,
    #             'project_act_type_id': project_act_type_id,
    #             'project_check_line_id': project_check_line_id,
    #             'description': description,
    #             'flag_category': flag_category,
    #             'project_create_date': project_create_date,
    #             'project_responsible': project_responsible,
    #             'status': status,
    #         }

    #         if custom_checklist_item:
    #             nc_values['custom_checklist_item'] = custom_checklist_item

    #         nc_values['seq_number'] = request.env['ir.sequence'].sudo().next_by_code('manually.set.flag') or 'New'

    #         # Create NC record
    #         nc = request.env['manually.set.flag'].sudo().create(nc_values)
    #         _logger.info(f"NC created successfully with ID: {nc.id}")

    #         # -------------------------------------------
    #         # Handle multiple normal images
    #         # -------------------------------------------
    #         image_list = data.get('images', [])
    #         image_urls = []
    #         if image_list:
    #             for img in image_list[:5]:
    #                 try:
    #                     base64_str = img.get('data')
    #                     filename = img.get('filename', 'image.jpg')
    #                     if ',' in base64_str:
    #                         base64_str = base64_str.split(',')[1]

    #                     img_record = request.env['manually.set.flag.images'].sudo().create({
    #                         'flag_id': nc.id,
    #                         'image': base64_str,
    #                         'filename': filename
    #                     })
    #                     image_urls.append(f"/web/image/{img_record._name}/{img_record.id}/image")
    #                 except Exception as e:
    #                     _logger.error(f"Error adding image: {str(e)}")

    #         # -------------------------------------------
    #         # Handle multiple rectified images
    #         # -------------------------------------------
    #         rectified_list = data.get('rectified_images', [])
    #         rectified_urls = []
    #         if rectified_list:
    #             for img in rectified_list[:5]:
    #                 try:
    #                     base64_str = img.get('data')
    #                     filename = img.get('filename', 'rectified_image.jpg')
    #                     if ',' in base64_str:
    #                         base64_str = base64_str.split(',')[1]

    #                     rect_record = request.env['manually.set.flag.rectified.images'].sudo().create({
    #                         'flag_id': nc.id,
    #                         'rectified_image': base64_str,
    #                         'filename': filename
    #                     })
    #                     rectified_urls.append(f"/web/image/{rect_record._name}/{rect_record.id}/rectified_image")
    #                 except Exception as e:
    #                     _logger.error(f"Error adding rectified image: {str(e)}")

    #         # -------------------------------------------
    #         # Prepare Response
    #         # -------------------------------------------
    #         response_data = {
    #             'status': 'success',
    #             'nc_id': nc.id,
    #             'message': 'NC created successfully.',
    #             'nc_data': {
    #                 'seq_no': nc.seq_number,
    #                 'description': nc.description,
    #                 'flag_category': nc.flag_category,
    #                 'project_id': nc.project_info_id.id if nc.project_info_id else None,
    #                 'tower_id': project_tower_id,  # ✅ Real tower ID returned
    #                 'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
    #                 'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
    #                 'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
    #                 'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
    #                 'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
    #                 'project_create_date': nc.project_create_date,
    #                 'custom_checklist': nc.custom_checklist_item,
    #                 'images': image_urls,
    #                 'rectified_images': rectified_urls,
    #             }
    #         }

    #         # Send notification if needed
    #         if nc.project_responsible:
    #             try:
    #                 response_data['notification_status'] = self.send_notification(nc)
    #             except Exception as e:
    #                 _logger.error(f"Error sending notification: {str(e)}")
    #                 response_data['notification_status'] = {'error': str(e)}

    #         return response_data

    #     except Exception as e:
    #         _logger.error("Error creating NC: %s", str(e))
    #         _logger.exception("Full traceback:")
    #         return {
    #             'status': 'error',
    #             'message': f'Failed to create NC: {str(e)}'
    #         }, 500


    #when checker create nc goes to maker
    @restapi.method([(["/api/nc/create"], "POST")], auth="public")
    def create_nc(self):
        try:
            data = json.loads(request.httprequest.data)
          
            _logger.info("Received JSON request: %s", data)
           

            _logger.info("POST API for NC creation called")
            # _logger.info("=" * 80)
            # _logger.info("FULL REQUEST DATA:")
            # _logger.info(f"Images in request: {len(data.get('images', []))}")
            _logger.info(f"Rectified images in request: {len(data.get('rectified_images', []))}")

            
            # Log the actual structure of the first image if exists
            if data.get('image'):
                first_img = data.get('images')[0]
                _logger.info(f"First image type: {type(first_img)}")
                if isinstance(first_img, dict):
                    _logger.info(f"First image keys: {first_img.keys()}")
                    _logger.info(f"First image has 'data': {'data' in first_img}")
                    _logger.info(f"First image has 'filename': {'filename' in first_img}")
                else:
                    _logger.info(f"First image is string, length: {len(first_img) if isinstance(first_img, str) else 'N/A'}")
            
            if data.get('rectified_image'):
                first_rect = data.get('rectified_image')[0]
                _logger.info(f"First rectified image type: {type(first_rect)}")
                if isinstance(first_rect, dict):
                    _logger.info(f"First rectified image keys: {first_rect.keys()}")
                else:
                    _logger.info(f"First rectified image is string, length: {len(first_rect) if isinstance(first_rect, str) else 'N/A'}")
            _logger.info("=" * 80)

            # Extract incoming IDs (some may come from temp models)
            project_info_id = int(data.get('project_id')) if data.get('project_id') else None
            temp_tower_id = int(data.get('tower_id')) if data.get('tower_id') else None
            project_floor_id = int(data.get('floor_id')) if data.get('floor_id') else None
            project_flats_id = int(data.get('flat_id')) if data.get('flat_id') else None
            project_activity_id = int(data.get('activity_id')) if data.get('activity_id') else None
            project_act_type = int(data.get('activity_type_id')) if data.get('activity_type_id') else None
            project_check_line = int(data.get('id')) if data.get('id') else None
            project_responsible = int(data.get('project_responsible_id')) if data.get('project_responsible_id') else None

            # -------------------------------------------
            # 🔍 Resolve actual Tower ID from temp model
            # -------------------------------------------
            project_tower_id = None
            if temp_tower_id:
                tower_temp = request.env['project.info.tower.line.temp'].sudo().browse(temp_tower_id)
                if tower_temp and tower_temp.tower_id:
                    project_tower_id = tower_temp.tower_id.id
                    _logger.info(f"Resolved real Tower ID: {project_tower_id} from temp ID: {temp_tower_id}")
                else:
                    _logger.warning(f"No matching project.tower found for temp tower ID: {temp_tower_id}")
            else:
                _logger.warning("tower_id not provided or invalid in payload")

            # -------------------------------------------
            # Lookup checklist & activity type records
            # -------------------------------------------
            checklist_template_id = int(project_check_line) if project_check_line else None
            project_check_line_record = request.env['project.activity.type.name.line'].sudo().search([
                ('checklist_id', '=', checklist_template_id)
            ], limit=1)
            project_check_line_id = project_check_line_record.id if project_check_line_record else None

            activity_type_record = request.env['project.activity.name.line'].sudo().search([
                ('patn_id', '=', project_act_type)
            ], limit=1)
            project_act_type_id = activity_type_record.id if activity_type_record else None

            # Extract main data
            custom_checklist_item = data.get('custom_checklist_item')
            description = data.get('description')
            flag_category = data.get('flag_category')
            project_create_date = data.get('project_create_date')
            status = data.get('status')

            # -------------------------------------------
            # Prepare NC record
            # -------------------------------------------
            nc_values = {
                'project_info_id': project_info_id,
                'project_tower_id': project_tower_id,
                'project_floor_id': project_floor_id,
                'project_flats_id': project_flats_id,
                'project_activity_id': project_activity_id,
                'project_act_type_id': project_act_type_id,
                'project_check_line_id': project_check_line_id,
                'description': description,
                'flag_category': flag_category,
                'project_create_date': project_create_date,
                'project_responsible': project_responsible,
                'status': status,
            }

            if custom_checklist_item:
                nc_values['custom_checklist_item'] = custom_checklist_item

            nc_values['seq_number'] = request.env['ir.sequence'].sudo().next_by_code('manually.set.flag') or 'New'

            # Create NC record
            nc = request.env['manually.set.flag'].sudo().create(nc_values)
            _logger.info(f"NC created successfully with ID: {nc.id}")

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple normal images
            # -------------------------------------------
            image_list = data.get('image', [])
            image_urls = []
            image_errors = []
            
            _logger.info(f"Processing {len(image_list)} normal images for NC ID: {nc.id}")
            
            if image_list and len(image_list) > 0:
                for idx, img in enumerate(image_list[:5]):  # Limit to 5 images
                    try:
                        # Handle both object format {"data": "...", "filename": "..."} 
                        # and string format "base64string"
                        if isinstance(img, dict):
                            base64_str = img.get('data')
                            filename = img.get('filename', f'image_{idx+1}.jpg')
                        elif isinstance(img, str):
                            # If it's a string, treat it as base64 data directly
                            base64_str = img
                            filename = f'image_{idx+1}.jpg'
                        else:
                            error_msg = f"Image {idx+1}: Invalid format (not dict or string)"
                            _logger.error(error_msg)
                            image_errors.append(error_msg)
                            continue
                        
                        # Validate base64 data exists
                        if not base64_str:
                            error_msg = f"Image {idx+1}: No data provided"
                            _logger.error(error_msg)
                            image_errors.append(error_msg)
                            continue
                        
                        # Ensure filename has proper extension
                        if not filename or filename.strip() == '':
                            filename = f'image_{idx+1}.jpg'
                        elif '.' not in filename:
                            filename = f'{filename}.jpg'
                        
                        # Clean base64 string - remove data URI prefix if present
                        if isinstance(base64_str, str):
                            # Remove 'data:image/...;base64,' prefix
                            if 'base64,' in base64_str:
                                base64_str = base64_str.split('base64,')[-1]
                            # Remove any whitespace and newlines
                            base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                        
                        _logger.info(f"Creating image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                        
                        # Create image record
                        img_record = request.env['manually.set.flag.images'].sudo().create({
                            'flag_id': nc.id,
                            'image': base64_str,
                            'filename': filename
                        })
                        
                        _logger.info(f"✅ Image record created successfully with ID: {img_record.id}")
                        
                        # Generate URL for the image
                        image_url = f"/web/image/manually.set.flag.images/{img_record.id}/image"
                        image_urls.append({
                            'id': img_record.id,
                            'url': image_url,
                            'filename': filename
                        })
                        
                    except Exception as e:
                        error_msg = f"Image {idx+1} error: {str(e)}"
                        _logger.error(error_msg)
                        _logger.exception(f"Full traceback for image {idx+1}:")
                        image_errors.append(error_msg)
            
            _logger.info(f"Images processed: {len(image_urls)} successful, {len(image_errors)} failed")

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple rectified images
            # -------------------------------------------
            rectified_list = data.get('rectified_image', [])
            rectified_urls = []
            rectified_errors = []
            
            _logger.info(f"Processing {len(rectified_list)} rectified images for NC ID: {nc.id}")
            
            if rectified_list and len(rectified_list) > 0:
                for idx, img in enumerate(rectified_list[:5]):  # Limit to 5 images
                    try:
                        # Handle both object format {"data": "...", "filename": "..."} 
                        # and string format "base64string"
                        if isinstance(img, dict):
                            base64_str = img.get('data')
                            filename = img.get('filename', f'image_{idx+1}.jpg')
                        elif isinstance(img, str):
                            # If it's a string, treat it as base64 data directly
                            base64_str = img
                            filename = f'image_{idx+1}.jpg'
                        else:
                            error_msg = f"Image {idx+1}: Invalid format (not dict or string)"
                            _logger.error(error_msg)
                            rectified_errors.append(error_msg)
                            continue
                        
                        # Validate base64 data exists
                        if not base64_str:
                            error_msg = f"Image {idx+1}: No data provided"
                            _logger.error(error_msg)
                            rectified_errors.append(error_msg)
                            continue
                        
                        # Ensure filename has proper extension
                        if not filename or filename.strip() == '':
                            filename = f'image_{idx+1}.jpg'
                        elif '.' not in filename:
                            filename = f'{filename}.jpg'
                        
                        # Clean base64 string - remove data URI prefix if present
                        if isinstance(base64_str, str):
                            # Remove 'data:image/...;base64,' prefix
                            if 'base64,' in base64_str:
                                base64_str = base64_str.split('base64,')[-1]
                            # Remove any whitespace and newlines
                            base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                        
                        _logger.info(f"Creating rectified image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                        
                        # Create rectified image record
                        rect_record = request.env['manually.set.flag.rectified.images'].sudo().create({
                            'flag_id': nc.id,
                            'rectified_image': base64_str,
                            'filename': filename
                        })
                        
                        _logger.info(f"✅ Rectified image record created successfully with ID: {rect_record.id}")
                        
                        # Generate URL for the rectified image
                        rectified_url = f"/web/image/manually.set.flag.rectified.images/{rect_record.id}/rectified_image"
                        rectified_urls.append({
                            'id': rect_record.id,
                            'url': rectified_url,
                            'filename': filename
                        })
                        
                    except Exception as e:
                        error_msg = f"Rectified image {idx+1} error: {str(e)}"
                        _logger.error(error_msg)
                        _logger.exception(f"Full traceback for rectified image {idx+1}:")
                        rectified_errors.append(error_msg)
            
            _logger.info(f"Rectified images processed: {len(rectified_urls)} successful, {len(rectified_errors)} failed")

            # -------------------------------------------
            # Prepare Response   
            # -------------------------------------------
            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC generated successfully.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'project_id': nc.project_info_id.id if nc.project_info_id else None,
                    'tower_id': project_tower_id,
                    'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'activity_type_id_name': nc.project_act_type_id.patn_id.name if nc.project_act_type_id else None,
                    'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,  # ✅ Convert datetime to ISO string
                    'custom_checklist': nc.custom_checklist_item,
                    'images': image_urls,  # ✅ Returns array of objects with id, url, filename
                    'rectified_images': rectified_urls,  # ✅ Returns array of objects with id, url, filename
                },
                'images_processed': {
                    'normal': {
                        'total_sent': len(image_list),
                        'successfully_stored': len(image_urls),
                        'failed': len(image_errors)
                    },
                    'rectified': {
                        'total_sent': len(rectified_list),
                        'successfully_stored': len(rectified_urls),
                        'failed': len(rectified_errors)
                    }
                }
            }
            
            # Add error details if any images failed
            if image_errors:
                response_data['image_errors'] = image_errors
            if rectified_errors:
                response_data['rectified_image_errors'] = rectified_errors

            # Send notification if needed
            if nc.project_responsible:
                try:
                    response_data['notification_status'] = self.send_notification(nc)
                except Exception as e:
                    _logger.error(f"Error sending notification: {str(e)}")
                    response_data['notification_status'] = {'error': str(e)}

            _logger.info(f"✅ NC creation completed successfully.")
            return response_data

        except Exception as e:
            _logger.error("❌ Error creating NC: %s", str(e))
            _logger.exception("Full traceback:")
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500

    def send_notification(self, nc):
        """ Sends push notification to the responsible person """
        if not nc.project_responsible:
            return {'error': 'No responsible person assigned'}

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        # Conditional address logic
        if flat_name:
            location_detail = f"Flat/{flat_name}"
        elif floor_name:
            location_detail = f"Floor/{floor_name}"
        else:
            location_detail = ""

        seq_no = nc.seq_number
        # Get current user's name
        current_user_name = request.env.user.name if request.env.user else 'Unknown User'

        # Update the message
        message = f"{current_user_name} has created a {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f"/{location_detail}"
            message += "."
        title = message

        # Get Push Notification ID
        player_id, user_r = request.env['res.users'].sudo(
        ).get_player_id(nc.project_responsible.id)
        player_ids = [player_id] if player_id else []

        if not player_ids:
            return {'error': 'No push notification ID found for the responsible person'}

        # OneSignal API credentials
        app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
        rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

        # Data to send in the notification
        data = {
            "app_id": app_id,
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        # Convert data to JSON
        data_json = json.dumps(data)

        # URL for OneSignal REST API
        url = "https://onesignal.com/api/v1/notifications"

        # Headers for the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {rest_api_key}"
        }

        # Send the notification
        response = requests.post(url, data=data_json, headers=headers)

        # Log Notification Status
        status = 'sent' if response.status_code == 200 else 'failed'
        request.env['app.notification.log'].sudo().create({
            'title': title if status == 'sent' else f"{title} (Failed)",
            'message': message,
            'res_user_id': nc.project_responsible.id,
            'player_id': player_id,
            'seq_no': seq_no,
            'status': status,
            'table_id': nc.id,
            'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
            'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
        })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}


        '''


        # 11/11
            # @restapi.method([(["/api/nc/close"], 'POST')], auth="public")
            # def close_nc(self):
            #     try:
            #         data = json.loads(request.httprequest.data)
            #         _logger.info("POST API for NC close called")
            #         _logger.info("=" * 80)
            #         _logger.info(f"NC ID: {data.get('nc_id')}")
            #         _logger.info(f"Images in request: {len(data.get('image', []))}")
            #         _logger.info("=" * 80)

            #         nc_id = data.get('nc_id')
            #         status = data.get('status')
            #         description = data.get('description')

            #         if not nc_id or status != 'close':
            #             return {'status': 'error', 'message': 'Invalid NC ID or status'}, 400

            #         # Get the NC record first
            #         nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            #         if not nc.exists():
            #             return {'status': 'error', 'message': 'NC not found'}, 404

            #         # -------------------------------------------
            #         # Handle multiple rectified images
            #         # -------------------------------------------
            #         rectified_list = data.get('image', [])
            #         rectified_urls = []
            #         rectified_errors = []
                    
            #         _logger.info(f"Processing {len(rectified_list)} images for NC ID: {nc.id}")
                    
            #         # Process images in batches to avoid transaction issues
            #         if rectified_list and len(rectified_list) > 0:
            #             for idx, img in enumerate(rectified_list[:5]):  # Limit to 5 images
            #                 try:
            #                     # Handle both object format {"data": "...", "filename": "..."} 
            #                     # and string format "base64string"
            #                     if isinstance(img, dict):
            #                         base64_str = img.get('data')
            #                         filename = img.get('filename', f'rectified_close_{idx+1}.jpg')
            #                     elif isinstance(img, str):
            #                         base64_str = img
            #                         filename = f'rectified_close_{idx+1}.jpg'
            #                     else:
            #                         error_msg = f"Rectified image {idx+1}: Invalid format (not dict or string)"
            #                         _logger.error(error_msg)
            #                         rectified_errors.append(error_msg)
            #                         continue
                                
            #                     # Validate base64 data exists
            #                     if not base64_str:
            #                         error_msg = f"Rectified image {idx+1}: No data provided"
            #                         _logger.error(error_msg)
            #                         rectified_errors.append(error_msg)
            #                         continue
                                
            #                     # Ensure filename has proper extension
            #                     if not filename or filename.strip() == '':
            #                         filename = f'rectified_close_{idx+1}.jpg'
            #                     elif '.' not in filename:
            #                         filename = f'{filename}.jpg'
                                
            #                     # Clean base64 string - remove data URI prefix if present
            #                     if isinstance(base64_str, str):
            #                         if 'base64,' in base64_str:
            #                             base64_str = base64_str.split('base64,')[-1]
            #                         base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                                
            #                     _logger.info(f"Creating rectified image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                                
            #                     # Create rectified image record
            #                     rect_record = request.env['manually.set.flag.rectified.images'].sudo().create({
            #                         'flag_id': nc.id,
            #                         'rectified_image': base64_str,
            #                         'filename': filename,
            #                         'description': 'Closed NC rectified image'
            #                     })
                                
            #                     # Flush to ensure the record is written to database
            #                     rect_record.flush()
                                
            #                     if rect_record and rect_record.id:
            #                         _logger.info(f"✅ Rectified image record created successfully with ID: {rect_record.id}")
                                    
            #                         # Generate URL for the rectified image
            #                         rectified_url = f"/web/image/manually.set.flag.rectified.images/{rect_record.id}/rectified_image"
            #                         rectified_urls.append({
            #                             'id': rect_record.id,
            #                             'url': rectified_url,
            #                             'filename': filename
            #                         })
            #                     else:
            #                         _logger.error(f"❌ Rectified image record creation returned None or invalid ID")
                                    
            #                 except Exception as e:
            #                     error_msg = f"Rectified image {idx+1} error: {str(e)}"
            #                     _logger.error(error_msg)
            #                     _logger.exception(f"Full traceback for rectified image {idx+1}:")
            #                     rectified_errors.append(error_msg)
                    
            #         _logger.info(f"Rectified images processed: {len(rectified_urls)} successful, {len(rectified_errors)} failed")

            #         # Update NC status and description - do this AFTER images are created
            #         nc.write({
            #             'status': 'close',
            #             'description': description if description else nc.description,
            #         })
                    
            #         # Explicit flush to ensure write is committed
            #         nc.flush()
                    
            #         # Commit the transaction explicitly
            #         request.env.cr.commit()
                    
            #         _logger.info(f"✅ NC status updated to 'close' with ID: {nc.id}")
                    
            #         # Reload to verify changes
            #         nc.invalidate_cache()
            #         nc_reload = request.env['manually.set.flag'].sudo().browse(nc.id)
            #         actual_rectified = len(nc_reload.rectified_image_ids)
            #         _logger.info(f"📊 FINAL CHECK - Total rectified images in database for NC {nc.id}: {actual_rectified}")

            #         # Send notification to project responsible
            #         notification_status = None
            #         if nc.project_responsible:
            #             try:
            #                 notification_status = self.send_close_notification(nc)
            #             except Exception as e:
            #                 _logger.error(f"Error sending notification: {str(e)}")
            #                 notification_status = {'error': str(e)}

            #         # Prepare response
            #         response_data = {
            #             'status': 'success',
            #             'nc_id': nc.id,
            #             'message': 'NC closed successfully.',
            #             'nc_data': {
            #                 'seq_number': nc.seq_number,
            #                 'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
            #                 'project_id': nc.project_info_id.id if nc.project_info_id else None,
            #                 'tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
            #                 'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
            #                 'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
            #                 'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
            #                 'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
            #                 'checklist_id': nc.project_check_line_id.id if nc.project_check_line_id else None,
            #                 'description': nc.description,
            #                 'flag_category': nc.flag_category,
            #                 'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
            #                 'status': nc.status,  # ✅ Added status to confirm it's closed
            #                 'rectified_images': rectified_urls,
            #                 'total_rectified_images': actual_rectified,  # ✅ Total count from database
            #             },
            #             'images_processed': {
            #                 'rectified': {
            #                     'total_sent': len(rectified_list),
            #                     'successfully_stored': len(rectified_urls),
            #                     'failed': len(rectified_errors)
            #                 }
            #             },
            #             'notification_status': notification_status
            #         }
                    
            #         # Add error details if any images failed
            #         if rectified_errors:
            #             response_data['rectified_image_errors'] = rectified_errors

            #         return response_data, 200

            #     except Exception as e:
            #         _logger.error("❌ Error closing NC: %s", str(e))
            #         _logger.exception("Full traceback:")
            #         # Rollback transaction on error
            #         try:
            #             request.env.cr.rollback()
            #         except:
            #             pass
            #         return {'status': 'error', 'message': f'Failed to close NC: {str(e)}'}, 500

            # @restapi.method([(["/api/nc/close"], 'POST')], auth="public")
            # def close_nc(self):
            #     try:
            #         data = json.loads(request.httprequest.data)
            #         _logger.info("POST API for NC close called")
            #         _logger.info("=" * 80)
            #         _logger.info(f"NC ID: {data.get('nc_id')}")
            #         _logger.info(f"Images in request: {len(data.get('image', []))}")
            #         _logger.info("=" * 80)

            #         nc_id = data.get('nc_id')
            #         status = data.get('status')
            #         description = data.get('description')

            #         if not nc_id or status != 'close':
            #             return {'status': 'error', 'message': 'Invalid NC ID or status'}, 400

            #         # Get the NC record first
            #         nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            #         if not nc.exists():
            #             return {'status': 'error', 'message': 'NC not found'}, 404

            #         # -------------------------------------------
            #         # Handle multiple rectified images
            #         # -------------------------------------------
            #         rectified_list = data.get('image', [])
            #         rectified_urls = []
            #         rectified_errors = []
                    
            #         _logger.info(f"Processing {len(rectified_list)} images for NC ID: {nc.id}")
                    
            #         # Process images with validation
            #         if rectified_list and len(rectified_list) > 0:
            #             for idx, img in enumerate(rectified_list[:5]):  # Limit to 5 images
            #                 try:
            #                     # Handle both object format {"data": "...", "filename": "..."} 
            #                     # and string format "base64string"
            #                     if isinstance(img, dict):
            #                         base64_str = img.get('data')
            #                         filename = img.get('filename', f'rectified_close_{idx+1}.jpg')
            #                     elif isinstance(img, str):
            #                         base64_str = img
            #                         filename = f'rectified_close_{idx+1}.jpg'
            #                     else:
            #                         error_msg = f"Rectified image {idx+1}: Invalid format (not dict or string)"
            #                         _logger.error(error_msg)
            #                         rectified_errors.append(error_msg)
            #                         continue
                                
            #                     # Validate base64 data exists and is not empty
            #                     if not base64_str or not isinstance(base64_str, str):
            #                         error_msg = f"Rectified image {idx+1}: No data provided or invalid type"
            #                         _logger.error(error_msg)
            #                         rectified_errors.append(error_msg)
            #                         continue
                                
            #                     # Clean base64 string - remove data URI prefix if present
            #                     if 'base64,' in base64_str:
            #                         base64_str = base64_str.split('base64,')[-1]
            #                     base64_str = base64_str.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                                
            #                     # CRITICAL: Validate base64 string length and format
            #                     if len(base64_str) < 100:  # Minimum realistic image size
            #                         error_msg = f"Rectified image {idx+1}: Base64 string too short ({len(base64_str)} chars) - likely invalid or empty image"
            #                         _logger.error(error_msg)
            #                         rectified_errors.append(error_msg)
            #                         continue
                                
            #                     # Validate base64 string is properly formatted (length must be multiple of 4)
            #                     if len(base64_str) % 4 != 0:
            #                         # Try to pad the string
            #                         padding_needed = 4 - (len(base64_str) % 4)
            #                         if padding_needed != 4:
            #                             base64_str += '=' * padding_needed
            #                             _logger.warning(f"Rectified image {idx+1}: Added {padding_needed} padding characters")
                                
            #                     # Validate it's actually valid base64 by attempting to decode
            #                     try:
            #                         import base64
            #                         decoded = base64.b64decode(base64_str)
            #                         if len(decoded) < 100:  # Should be at least 100 bytes for a valid image
            #                             error_msg = f"Rectified image {idx+1}: Decoded data too small ({len(decoded)} bytes) - not a valid image"
            #                             _logger.error(error_msg)
            #                             rectified_errors.append(error_msg)
            #                             continue
            #                     except Exception as decode_err:
            #                         error_msg = f"Rectified image {idx+1}: Invalid base64 encoding - {str(decode_err)}"
            #                         _logger.error(error_msg)
            #                         rectified_errors.append(error_msg)
            #                         continue
                                
            #                     # Ensure filename has proper extension
            #                     if not filename or filename.strip() == '':
            #                         filename = f'rectified_close_{idx+1}.jpg'
            #                     elif '.' not in filename:
            #                         filename = f'{filename}.jpg'
                                
            #                     _logger.info(f"Creating rectified image record {idx+1}: filename={filename}, data_length={len(base64_str)}, decoded_size={len(decoded)} bytes")
                                
            #                     # Create rectified image record
            #                     rect_record = request.env['manually.set.flag.rectified.images'].sudo().create({
            #                         'flag_id': nc.id,
            #                         'rectified_image': base64_str,
            #                         'filename': filename,
            #                         'description': 'Closed NC rectified image'
            #                     })
                                
            #                     if rect_record and rect_record.id:
            #                         _logger.info(f"✅ Rectified image record created successfully with ID: {rect_record.id}")
                                    
            #                         # Use proper Odoo image URL format with unique parameter to avoid caching
            #                         import time
            #                         timestamp = int(time.time())
            #                         rectified_url = f"/web/image/manually.set.flag.rectified.images/{rect_record.id}/rectified_image?unique={timestamp}"
                                    
            #                         rectified_urls.append({
            #                             'id': rect_record.id,
            #                             'url': rectified_url,
            #                             'filename': filename
            #                         })
            #                     else:
            #                         error_msg = f"Rectified image {idx+1}: Record creation returned None or invalid ID"
            #                         _logger.error(error_msg)
            #                         rectified_errors.append(error_msg)
                                    
            #                 except Exception as e:
            #                     error_msg = f"Rectified image {idx+1} error: {str(e)}"
            #                     _logger.error(error_msg)
            #                     _logger.exception(f"Full traceback for rectified image {idx+1}:")
            #                     rectified_errors.append(error_msg)
                    
            #         _logger.info(f"Rectified images processed: {len(rectified_urls)} successful, {len(rectified_errors)} failed")

            #         # Update NC status and description
            #         nc.write({
            #             'status': 'close',
            #             'description': description if description else nc.description,
            #         })
                    
            #         _logger.info(f"✅ NC status updated to 'close' with ID: {nc.id}")
                    
            #         # Refresh the record to get updated data (using Odoo 16+ method)
            #         nc.invalidate_recordset()
            #         actual_rectified = len(nc.rectified_image_ids)
            #         _logger.info(f"📊 FINAL CHECK - Total rectified images in database for NC {nc.id}: {actual_rectified}")

            #         # Send notification to project responsible
            #         notification_status = None
            #         if nc.project_responsible:
            #             try:
            #                 notification_status = self.send_close_notification(nc)
            #             except Exception as e:
            #                 _logger.error(f"Error sending notification: {str(e)}")
            #                 notification_status = {'error': str(e)}

            #         # Prepare response
            #         response_data = {
            #             'status': 'success',
            #             'nc_id': nc.id,
            #             'message': 'NC closed successfully.',
            #             'nc_data': {
            #                 'seq_number': nc.seq_number,
            #                 'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
            #                 'project_id': nc.project_info_id.id if nc.project_info_id else None,
            #                 'tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
            #                 'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
            #                 'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
            #                 'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
            #                 'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
            #                 'checklist_id': nc.project_check_line_id.id if nc.project_check_line_id else None,
            #                 'description': nc.description,
            #                 'flag_category': nc.flag_category,
            #                 'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
            #                 'status': nc.status,
            #                 'rectified_images': rectified_urls,
            #                 'total_rectified_images': actual_rectified,
            #             },
            #             'images_processed': {
            #                 'rectified': {
            #                     'total_sent': len(rectified_list),
            #                     'successfully_stored': len(rectified_urls),
            #                     'failed': len(rectified_errors)
            #                 }
            #             },
            #             'notification_status': notification_status
            #         }
                    
            #         # Add error details if any images failed
            #         if rectified_errors:
            #             response_data['rectified_image_errors'] = rectified_errors
            #             _logger.warning(f"⚠️ Some images failed to process: {rectified_errors}")

            #         return response_data, 200

            #     except Exception as e:
            #         _logger.error("❌ Error closing NC: %s", str(e))
            #         _logger.exception("Full traceback:")
            #         return {'status': 'error', 'message': f'Failed to close NC: {str(e)}'}, 500


            '''

    #maker submit nc to approver 
    @restapi.method([(["/api/nc/submit"], 'POST')], auth="public")
    def close_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called %s", data)

            nc_id = data.get('nc_id')
            status = data.get('status')
            # image = data.get('image')
            overall_remarks = data.get('overall_remarks')


          
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple normal images
            # -------------------------------------------
            image_list = data.get('image', [])
            image_urls = []
            image_errors = []
            
            _logger.info(f"Processing {len(image_list)} normal images for NC ID: {nc.id}")
            
            image_list = data.get('image', [])
            image_urls = []
            image_errors = []

            valid_images = [img for img in image_list if img and isinstance(img, (dict, str))]

            if valid_images:
                for idx, img in enumerate(valid_images[:5]):
                    try:
                        # Handle dict format
                        if isinstance(img, dict):
                            base64_str = img.get('data')
                            filename = img.get('filename', f'image_{idx+1}.jpg')

                        # Handle string format
                        elif isinstance(img, str):
                            base64_str = img
                            filename = f'image_{idx+1}.jpg'

                        # Reject blanks
                        if not base64_str or base64_str.strip() == "":
                            continue

                        # Remove prefix
                        if 'base64,' in base64_str:
                            base64_str = base64_str.split('base64,')[-1]

                        base64_str = base64_str.strip()

                        img_record = request.env['manually.set.flag.images'].sudo().create({
                            'flag_id': nc.id,
                            'image': base64_str,
                            'filename': filename
                        })

                        image_urls.append({
                            'id': img_record.id,
                            'url': f"/web/image/manually.set.flag.images/{img_record.id}/image",
                            'filename': filename
                        })

                    except Exception as e:
                        image_errors.append(str(e))

            _logger.info(f"Images processed: {len(image_urls)} successful, {len(image_errors)} failed")

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple rectified images
            # -------------------------------------------
            # rectified_list = data.get('rectified_image', [])
            # rectified_urls = []
            # rectified_errors = []
            
            # _logger.info(f"Processing {len(rectified_list)} rectified images for NC ID: {nc.id}")
            
            # if rectified_list and len(rectified_list) > 0:
            #     for idx, img in enumerate(rectified_list[:5]):  # Limit to 5 images
            #         try:
            #             # Handle both object format {"data": "...", "filename": "..."} 
            #             # and string format "base64string"
            #             if isinstance(img, dict):
            #                 base64_str = img.get('data')
            #                 filename = img.get('filename', f're_image_{idx+1}.jpg')
            #             elif isinstance(img, str):
            #                 # If it's a string, treat it as base64 data directly
            #                 base64_str = img
            #                 filename = f'image_{idx+1}.jpg'
            #             else:
            #                 error_msg = f"Image {idx+1}: Invalid format (not dict or string)"
            #                 _logger.error(error_msg)
            #                 rectified_errors.append(error_msg)
            #                 continue
                        
            #             # Validate base64 data exists
            #             if not base64_str:
            #                 error_msg = f"Image {idx+1}: No data provided"
            #                 _logger.error(error_msg)
            #                 rectified_errors.append(error_msg)
            #                 continue
                        
            #             # Ensure filename has proper extension
            #             if not filename or filename.strip() == '':
            #                 filename = f'image_{idx+1}.jpg'
            #             elif '.' not in filename:
            #                 filename = f'{filename}.jpg'
                        
            #             # Clean base64 string - remove data URI prefix if present
            #             if isinstance(base64_str, str):
            #                 # Remove 'data:image/...;base64,' prefix
            #                 if 'base64,' in base64_str:
            #                     base64_str = base64_str.split('base64,')[-1]
            #                 # Remove any whitespace and newlines
            #                 base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                        
            #             _logger.info(f"Creating rectified image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                        
            #             # Create rectified image record
            #             rect_record = request.env['manually.set.flag.rectified.images'].sudo().create({
            #                 'flag_id': nc.id,
            #                 'rectified_image': base64_str,
            #                 'filename': filename
            #             })
                        
            #             _logger.info(f"✅ Rectified image record created successfully with ID: {rect_record.id}")
                        
            #             # Generate URL for the rectified image
            #             rectified_url = f"/web/image/manually.set.flag.rectified.images/{rect_record.id}/rectified_image"
            #             rectified_urls.append({
            #                 'id': rect_record.id,
            #                 'url': rectified_url,
            #                 'filename': filename
            #             })
                        
            #         except Exception as e:
            #             error_msg = f"Rectified image {idx+1} error: {str(e)}"
            #             _logger.error(error_msg)
            #             _logger.exception(f"Full traceback for rectified image {idx+1}:")
            #             rectified_errors.append(error_msg)
            
            # _logger.info(f"Rectified images processed: {len(rectified_urls)} successful, {len(rectified_errors)} failed")


          
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            # image_data = None
            # rimage_data = image

            # if rimage_data:
            #     try:
            #         image_data = rimage_data.split(',')[1]
            #         decoded_image = base64.b64decode(
            #             image_data)

            #         attachment = self.env['ir.attachment'].sudo().create({
            #             'name': 'image.jpg',
            #             'type': 'binary',
            #             'datas': base64.b64encode(decoded_image),
            #             'res_model': 'manually.set.flag',
            #             'res_id': nc.id,
            #         })
            #     except Exception as e:
            #         _logger.error(f"Error decoding image: {str(e)}")


            if not nc.exists():
                return {'status': 'error', 'message': 'NC not found'}, 404

            # image_data = None
            # if image:
            #     try:
            #         image_data = image.split(',')[1]
            #         decoded_image = base64.b64decode(image_data)

            #         request.env['ir.attachment'].sudo().create({
            #             'name': 'closed_nc_image.jpg',
            #             'type': 'binary',
            #             'datas': base64.b64encode(decoded_image),
            #             'res_model': 'manually.set.flag',
            #             'res_id': nc.id,
            #         })
            #     except Exception as e:
            #         _logger.error(f"Error decoding image: {str(e)}")

            # Update NC status
            nc.write({
                'status': 'submit',
                'overall_remarks': overall_remarks,
                # 'image': image_urls,
            })

            _logger.info("NC status updated to 'submit' with ID: %s", nc.id)

            # Send notification to project responsible
            # if nc.project_responsible:

            # 🔕 Hide previous notification from Maker side after submit
            try:
                app_log_obj = request.env['app.notification.log'].sudo()

                logs_to_hide = app_log_obj.search([
                    ('table_id', '=', nc.id),                 # Same NC
                    ('res_user_id', '=', request.env.user.id),# Maker (current user)
                    ('hide_notification', '=', False),
                ])

                if logs_to_hide:
                    logs_to_hide.write({'hide_notification': True})
                    _logger.info(
                        "Maker NC notifications hidden after submit: %s",
                        logs_to_hide.ids
                    )

            except Exception as e:
                _logger.error("Failed to hide maker NC notifications: %s", e)


            notification_status = self.send_close_notification(nc)

            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC closed successfully.',
                'nc_data': {
                    'seq_number': nc.seq_number,
                    'project_create_date': nc.project_create_date,
                    'project_id': nc.project_info_id.id,
                    'tower_id': nc.project_tower_id.id,
                    'floor_id': nc.project_floor_id.id,
                    'flat_id': nc.project_flats_id.id,
                    'activity_id': nc.project_activity_id.id,
                    'activity_type_id': nc.project_act_type_id.id,
                    'id': nc.project_check_line_id.id,
                    'description': nc.description,
                    'overall_remarks': nc.overall_remarks,
                    'flag_category': nc.flag_category,
                    'rectified_image': nc.rectified_image,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'image': image_urls,
                },
                'notification_status': notification_status
            }
            _logger.info("response data: %s", response_data)

            return response_data, 200

        except Exception as e:
            _logger.error("Error submitting NC: %s", e)
            return {'status': 'error', 'message': f'Failed to submit NC: {str(e)}'}, 500

    def send_close_notification(self, nc):
        _logger.info("=== Sending Approver Notification for NC ID %s ===", nc.id)

        tower = nc.project_tower_id
        if not tower or not tower.assigned_to_ids:
            _logger.error("No assigned users found for tower. Cannot find approvers.")
            return {"error": "No approvers found"}

        approver_users = []

        # 🔍 EXACT SAME LOGIC AS button_checking_done (group.name == 'Approver')
        for user in tower.assigned_to_ids:
            for group in user.groups_id:
                if group.name == "Approver":
                    approver_users.append(user)

        _logger.info("Approvers Found: %s", [u.name for u in approver_users])

        if not approver_users:
            _logger.error("No Approver users assigned to this tower.")
            return {"error": "Approver not assigned to tower"}

        # Build Notification Message
        current_user = request.env.user
        seq_no = nc.seq_number
        
        project_name = nc.project_info_id.name or ''
        tower_name = nc.project_tower_id.name or ''
        floor_name = nc.project_floor_id.name or ''
        flat_name = nc.project_flats_id.name or ''

        category = nc.flag_category or ''

        # message = f"{current_user.name} has submitted the {category} for {project_name}/{tower_name}."
        # title = f"NC {seq_no} Submitted"
        # title = f"{current_user.name} has submitted the {category} for {project_name}/{tower_name}."
        # location_text = f"{project_name}/{tower_name}/{floor_name}/{flat_name}"

        parts = [project_name, tower_name, floor_name, flat_name]
        location_text = "/".join([p for p in parts if p])

        message = f"{current_user.name} has submitted the {category} for {location_text}."
        title = f"{current_user.name} has submitted the {category} for {location_text}."


        notification_obj = request.env['app.notification']
        log_obj = request.env['app.notification.log']

        sent = False
        failed_users = []

        # 🔔 Send to all approvers
        for approver in approver_users:
            player_id, _ = request.env['res.users'].sudo().get_player_id(approver.id)

            if player_id:
                try:
                    notification_obj.send_push_notification(
                        title,
                        [player_id],
                        message,
                        [approver.id],
                        seq_no,
                        'close_nc',
                        nc
                    )
                    sent = True

                    log_obj.sudo().create({
                        'title': title,
                        'message': message,
                        'res_user_id': approver.id,
                        'status': "sent",
                        'seq_no': seq_no,
                        'table_id': nc.id,
                        'project_info_id': nc.project_info_id.id,
                        'tower_id': nc.project_tower_id.id
                    })
                except Exception as e:
                    _logger.error("Failed sending to %s: %s", approver.name, e)
                    failed_users.append(approver.name)
            else:
                failed_users.append(approver.name)

        if not sent:
            return {"error": f"No notifications sent. Failed for {failed_users}"}

        return {"success": True, "message": "Notifications sent to approver(s)"}


    @restapi.method([(["/api/approver/nc/close"], "POST")], auth="public")
    def approver_close_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called")

            nc_id = data.get('nc_id')
            approver_remark = data.get('approver_remark')
            approver_close_images = data.get('approver_close_images', [])

            
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            if not nc_id:
                return {'status': 'error', 'message': 'NC ID missing'}, 400

            if not nc.exists():
                return {'status': 'error', 'message': 'NC not found'}, 404

            if nc.status != 'submit':
                return {'status': 'error', 'message': 'NC status must be submit'}, 400
                        
            nc.write({
                'status': 'close',
                'approver_remark': approver_remark,
                
            })
            # 🔕 Hide approver notification after NC is closed
            try:
                app_log_obj = request.env['app.notification.log'].sudo()

                logs_to_hide = app_log_obj.search([
                    ('table_id', '=', nc.id),                     # Same NC
                    ('res_user_id', '=', request.env.user.id),    # Current approver
                    ('hide_notification', '=', False),
                    ('status', '=', 'sent'),
                ])

                if logs_to_hide:
                    logs_to_hide.write({'hide_notification': True})
                    _logger.info(
                        "Approver NC notifications hidden after close: %s",
                        logs_to_hide.ids
                    )

            except Exception as e:
                _logger.error("Failed to hide approver NC notifications: %s", e)

            for idx, img in enumerate(approver_close_images[:5]):
                try:
                    if isinstance(img, dict):
                        base64_str = img.get('data') or img.get('approver_close_img')
                        filename = img.get('filename', f'close_{idx+1}.jpg')

                    elif isinstance(img, str):
                        base64_str = img
                        filename = f'close_{idx+1}.jpg'

                    if not base64_str:
                        continue

                    if 'base64,' in base64_str:
                        base64_str = base64_str.split('base64,')[-1]

                    request.env['manually.set.flag.approver.close.images'].sudo().create({
                        'flag_id': nc.id,
                        'approver_close_img': base64_str,   
                        'filename': filename,
                    })

                except Exception as e:
                    _logger.error("Approver Close image error: %s", e)
            

            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC closed successfully.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'project_id': nc.project_info_id.id if nc.project_info_id else None,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'custom_checklist': nc.custom_checklist_item,
                    'approver_remark': nc.approver_remark
                    # 'images': nc.image_urls, 
                    # 'rectified_images': nc.rectified_urls, 
                },
                
            }            

            # Send notification if needed
            if nc.project_responsible:
                try:
                    response_data['notification_status'] = self.send_close_nc_notification(nc)
                except Exception as e:
                    _logger.error(f"Error sending notification: {str(e)}")
                    response_data['notification_status'] = {'error': str(e)}

            _logger.info(f"✅ NC creation completed successfully.")
            return response_data

        except Exception as e:
            _logger.error("❌ Error creating NC: %s", str(e))
            _logger.exception("Full traceback:")
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500

    def send_close_nc_notification(self, nc):
        """ Sends push notification to NC creator & project responsible """

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        current_user = request.env.user
        current_user_name = current_user.name if current_user else 'Unknown User'

        # Conditional address logic
        if flat_name:
            location_detail = f"Flat/{flat_name}"
        elif floor_name:
            location_detail = f"Floor/{floor_name}"
        else:
            location_detail = ""

        seq_no = nc.seq_number

        # 💡 User who created the NC
        creator_user = nc.create_uid
        # creator_name = creator_user.name if creator_user else "Unknown User"

        # 📝 Notification Message
        message = f"{current_user_name} has closed a {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f"/{location_detail}"
        message += "."
        title = message

        # 🎯 Target users
        player_ids = []

        # Project Responsible
        if nc.project_responsible:
            pr_player, _ = request.env['res.users'].sudo().get_player_id(nc.project_responsible.id)
            if pr_player:
                player_ids.append(pr_player)

        # NC Creator
        if creator_user:
            creator_player, _ = request.env['res.users'].sudo().get_player_id(creator_user.id)
            if creator_player:
                player_ids.append(creator_player)

        if not player_ids:
            return {'error': 'No push notification IDs found for recipients'}

        # OneSignal Push
        data = {
            "app_id": "3dbd7654-0443-42a0-b8f1-10f0b4770d8d",
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"
        }

        response = requests.post("https://onesignal.com/api/v1/notifications",
                                data=json.dumps(data),
                                headers=headers)

        status = 'sent' if response.status_code == 200 else 'failed'

        # Logging notification for both NC creator & project responsible
        for user in [creator_user, nc.project_responsible]:
            if user:
                request.env['app.notification.log'].sudo().create({
                    'title': title if status == 'sent' else f"{title} (Failed)",
                    'message': message,
                    'res_user_id': user.id,
                    'status': status,
                    'seq_no': seq_no,
                    'table_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
                })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}


    @restapi.method([(["/api/approver/nc/reject"], "POST")], auth="public")
    def approver_reject_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC (approver_reject) called")

            nc_id = data.get('nc_id')
            approver_remark = data.get('approver_remark')
            close_images = data.get('close_images', [])

            
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            if not nc_id:
                return {'status': 'error', 'message': 'NC ID missing'}, 400

            if not nc.exists():
                return {'status': 'error', 'message': 'NC not found'}, 404

            if nc.status != 'submit':
                return {'status': 'error', 'message': 'NC status must be submit'}, 400
                        
            nc.write({
                'status': 'approver_reject',
                'approver_remark': approver_remark
            })
            # 🔕 Hide approver notification after NC reject (soft hide)
            try:
                app_log_obj = request.env['app.notification.log'].sudo()

                logs_to_hide = app_log_obj.search([
                    ('table_id', '=', nc.id),                     # Same NC
                    ('res_user_id', '=', request.env.user.id),    # Current approver
                    ('hide_notification', '=', False),
                    ('status', '=', 'sent'),
                ])

                if logs_to_hide:
                    logs_to_hide.write({'hide_notification': True})
                    _logger.info(
                        "Approver NC notifications hidden after reject: %s",
                        logs_to_hide.ids
                    )

            except Exception as e:
                _logger.error("Failed to hide approver NC notifications on reject: %s", e)
            # valid_images = [img for img in close_images if img and isinstance(img, (dict, str))]

            for idx, img in enumerate(close_images[:5]):
                try:
                    if isinstance(img, dict):
                        base64_str = img.get('data') or img.get('approver_image')
                        filename = img.get('filename', f'close_{idx+1}.jpg')

                    elif isinstance(img, str):
                        base64_str = img
                        filename = f'close_{idx+1}.jpg'

                    if not base64_str:
                        continue

                    # ✅ remove base64 prefix
                    if 'base64,' in base64_str:
                        base64_str = base64_str.split('base64,')[-1]

                    request.env['manually.set.flag.close.images'].sudo().create({
                        'flag_id': nc.id,
                        'approver_image': base64_str,   # ✅ CORRECT
                        'filename': filename,
                    })

                except Exception as e:
                    _logger.error("Close image error: %s", e)

            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'approver rejected the Nc changes.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'project_id': nc.project_info_id.id if nc.project_info_id else None,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'custom_checklist': nc.custom_checklist_item,
                    'approver_remark': nc.approver_remark
                    # 'images': nc.image_urls, 
                    # 'rectified_images': nc.rectified_urls, 
                },
                
            }            

            # Send notification if needed
            if nc.project_responsible:
                try:
                    response_data['notification_status'] = self.send_reject_nc_notification(nc)
                except Exception as e:
                    _logger.error(f"Error sending notification: {str(e)}")
                    response_data['notification_status'] = {'error': str(e)}

            _logger.info(f"✅ NC creation completed successfully.")
            return response_data

        except Exception as e:
            _logger.error("❌ Error creating NC: %s", str(e))
            _logger.exception("Full traceback:")
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500

    def send_reject_nc_notification(self, nc):
        """ Sends push notification to NC creator & project responsible """

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        current_user = request.env.user
        current_user_name = current_user.name if current_user else 'Unknown User'

        # Conditional address logic
        if flat_name:
            location_detail = f"Flat/{flat_name}"
        elif floor_name:
            location_detail = f"Floor/{floor_name}"
        else:
            location_detail = ""

        seq_no = nc.seq_number

        # 💡 User who created the NC
        creator_user = nc.create_uid
        # creator_name = creator_user.name if creator_user else "Unknown User"

        # 📝 Notification Message
        message = f"{current_user_name} has rejected a {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f"/{location_detail}"
        message += "."
        title = message

        # 🎯 Target users
        player_ids = []

        # Project Responsible
        if nc.project_responsible:
            pr_player, _ = request.env['res.users'].sudo().get_player_id(nc.project_responsible.id)
            if pr_player:
                player_ids.append(pr_player)

        # # NC Creator
        # if creator_user:
        #     creator_player, _ = request.env['res.users'].sudo().get_player_id(creator_user.id)
        #     if creator_player:
        #         player_ids.append(creator_player)

        # if not player_ids:
        #     return {'error': 'No push notification IDs found for recipients'}

        # OneSignal Push
        data = {
            "app_id": "3dbd7654-0443-42a0-b8f1-10f0b4770d8d",
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"
        }

        response = requests.post("https://onesignal.com/api/v1/notifications",
                                data=json.dumps(data),
                                headers=headers)

        status = 'sent' if response.status_code == 200 else 'failed'

        # Logging notification for both NC creator & project responsible
        for user in [nc.project_responsible]:
            if user:
                request.env['app.notification.log'].sudo().create({
                    'title': title if status == 'sent' else f"{title} (Failed)",
                    'message': message,
                    'res_user_id': user.id,
                    'status': status,
                    'seq_no': seq_no,
                    'table_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
                })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}



#######################old flow for sending notification
    # def send_close_notification(self, nc):
        
    #     if not nc.project_responsible and not request.env.user:
    #         return {'error': 'No recipient found for notification'}

    #     project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
    #     tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
    #     flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
    #     seq_no = nc.seq_number
    #     current_user = request.env.user  # Get the user who is closing the NC
    #     current_user_name = current_user.name if current_user else 'Unknown User'
    #     flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
    #     floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

    #     # Conditional address logic
    #     if flat_name:
    #         location_detail = f"Flat/{flat_name}"
    #     elif floor_name:
    #         location_detail = f"Floor/{floor_name}"
    #     else:
    #         location_detail = ""

    #     message = f"{current_user_name} has closed the {flag_category} for {project_name}/{tower_name}"
    #     if location_detail:
    #         message += f"/{location_detail}"
    #         message += "."
    #     title = message

    #     # Get player IDs for both project responsible & closing user
    #     player_ids = []

    #     # Project Responsible
    #     if nc.project_responsible:
    #         project_responsible_player, _ = request.env['res.users'].sudo(
    #         ).get_player_id(nc.project_responsible.id)
    #         if project_responsible_player:
    #             player_ids.append(project_responsible_player)

    #     # User who closed the NC
    #     if current_user:
    #         closing_user_player, _ = request.env['res.users'].sudo(
    #         ).get_player_id(current_user.id)
    #         if closing_user_player:
    #             player_ids.append(closing_user_player)

    #     if not player_ids:
    #         return {'error': 'No push notification IDs found for recipients'}

    #     app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
    #     rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

    #     data = {
    #         "app_id": app_id,
    #         "include_player_ids": player_ids,
    #         "contents": {"en": message},
    #         "headings": {"en": title},
    #     }

    #     data_json = json.dumps(data)
    #     url = "https://onesignal.com/api/v1/notifications"
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Basic {rest_api_key}"
    #     }

    #     response = requests.post(url, data=data_json, headers=headers)
    #     status = 'sent' if response.status_code == 200 else 'failed'
 
    #     # Log notification for both users
    #     for user_id in [nc.project_responsible.id, current_user.id]:
    #         if user_id:
    #             request.env['app.notification.log'].sudo().create({
    #                 'title': title if status == 'sent' else f"{title} (Failed)",
    #                 'message': message,
    #                 'res_user_id': user_id,
    #                 'status': status,
    #                 'seq_no': seq_no,
    #                 'table_id': nc.id,
    #                 'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
    #                 'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
    #             })

    #     return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}

  
  
  
  #########################################################
    # @restapi.method([(["/api/nc/fetch_all"], "POST")], auth="public")
    # def fetch_all_nc(self):
    #     try:
    #         _logger.info("POST API for fetching all NC called")
    #         _logger.info("Received request at /api/nc/fetch_all")

    #         # Fetch all tasks
    #         ncs = request.env['manually.set.flag'].sudo().search([])

    #         # Prepare response data for all tasks
    #         nc_data = []
    #         for nc in ncs:
    #             _logger.debug("Processing nc ID: %s", nc.id)
    #             nc_data.append({
    #                 'seq_number': nc.seq_number,
    #                 'nc_id': nc.id,
    #                 'project_info_id': nc.project_info_id.id,
    #                 'project_info_name': nc.project_info_id.name,
    #                 'project_tower_id': nc.project_tower_id.id,
    #                 'project_tower_name': nc.project_tower_id.name,
    #                 'project_floor_id': nc.project_floor_id.id,
    #                 'project_floor_name': nc.project_floor_id.name,
    #                 'project_flats_id': nc.project_flats_id.id,
    #                 'project_flats_name': nc.project_flats_id.name,

    #                 'project_activity_id': nc.project_activity_id.id,
    #                 'project_activity_name': nc.project_activity_id.name,

    #                 # # 'project_activity_name': nc.project_activity_id.name,
    #                 # 'project_activity_name': nc.project_activity_id.name if nc.project_activity_id else '',
    #                 # 'project_activity_name': nc.project_activity_id.name if nc.project_activity_id.exists() else '',
    #                 'project_act_type_id': nc.project_act_type_id.id,
    #                 # 'project_act_type_name': nc.project_act_type_id.patn_id.name,
    #                 'project_act_type_name': nc.project_act_type_id.name,


    #                 'project_check_line_id': nc.project_check_line_id.id,
    #                 # 'project_check_line_name': nc.project_check_line_id,
    #                 'project_check_line_name': nc.project_check_line_id.checklist_id.name,
    #                 # 'project_check_line_name': nc.project_check_line_id.checklist_template_id.name,
    #                 'custom_checklist_item': nc.custom_checklist_item,

    #                 'project_create_date': nc.project_create_date,
    #                 'project_responsible': nc.project_responsible.name,
    #                 'description': nc.description,
    #                 'flag_category': nc.flag_category,
    #                 'rectified_image': nc.rectified_image,
    #             })

    #         _logger.info("Total ncs fetched: %s", len(ncs))

    #         return {
    #             'status': 'success',
    #             'ncs': nc_data
    #         }, 200

    #     except Exception as e:
    #         _logger.error("Error fetching ncs: %s", e, exc_info=True)
    #         return {
    #             'status': 'error',
    #             'message': 'Failed to fetch ncs.',
    #             'error_details': str(e)
    #         }, 500


#  working
    # @restapi.method([(["/api/nc/fetch_all"], "POST")], auth="public")
    # def fetch_all_nc(self):
    #     try:
    #         _logger.info("POST API for fetching all NC called")
    #         _logger.info("Received request at /api/nc/fetch_all")

    #         # Fetch all NCs
    #         ncs = request.env['manually.set.flag'].sudo().search([])

    #         # Prepare response data for all NCs
    #         nc_data = []
    #         for nc in ncs:
    #             _logger.debug("Processing nc ID: %s", nc.id)
                
    #             # Fetch all images for this NC
    #             image_urls = []
    #             for img in nc.image_ids:
    #                 image_urls.append({
    #                     'id': img.id,
    #                     'url': f"/web/image/manually.set.flag.images/{img.id}/image",
    #                     'filename': img.filename or 'image.jpg'
    #                 })
                
    #             # Fetch all rectified images for this NC
    #             rectified_image_urls = []
    #             for img in nc.rectified_image_ids:
    #                 rectified_image_urls.append({
    #                     'id': img.id,
    #                     'url': f"/web/image/manually.set.flag.rectified.images/{img.id}/rectified_image",
    #                     'filename': img.filename or 'rectified_image.jpg'
    #                 })
                
    #             nc_data.append({
    #                 'seq_number': nc.seq_number,
    #                 'nc_id': nc.id,
    #                 'project_info_id': nc.project_info_id.id if nc.project_info_id else None,
    #                 'project_info_name': nc.project_info_id.name if nc.project_info_id else '',
    #                 'project_tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
    #                 'project_tower_name': nc.project_tower_id.name if nc.project_tower_id else '',
    #                 'project_floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
    #                 'project_floor_name': nc.project_floor_id.name if nc.project_floor_id else '',
    #                 'project_flats_id': nc.project_flats_id.id if nc.project_flats_id else None,
    #                 'project_flats_name': nc.project_flats_id.name if nc.project_flats_id else '',
    #                 'project_activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
    #                 'project_activity_name': nc.project_activity_id.name if nc.project_activity_id else '',
    #                 'project_act_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
    #                 'project_act_type_name': nc.project_act_type_id.name if nc.project_act_type_id else '',
    #                 'project_check_line_id': nc.project_check_line_id.id if nc.project_check_line_id else None,
    #                 'project_check_line_name': nc.project_check_line_id.checklist_id.name if nc.project_check_line_id and nc.project_check_line_id.checklist_id else '',
    #                 'custom_checklist_item': nc.custom_checklist_item or '',
    #                 'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
    #                 'project_responsible': nc.project_responsible.name if nc.project_responsible else '',
    #                 'project_responsible_id': nc.project_responsible.id if nc.project_responsible else None,
    #                 'description': nc.description or '',
    #                 'flag_category': nc.flag_category or '',
    #                 'status': nc.status or '',
    #                 'images': image_urls,  # ✅ Array of image objects
    #                 'rectified_images': rectified_image_urls,  # ✅ Array of rectified image objects
    #             })

    #         _logger.info("Total ncs fetched: %s", len(ncs))

    #         return {
    #             'status': 'success',
    #             'ncs': nc_data
    #         }, 200

    #     except Exception as e:
    #         _logger.error("Error fetching ncs: %s", e, exc_info=True)
    #         return {
    #             'status': 'error',
    #             'message': 'Failed to fetch ncs.',
    #             'error_details': str(e)
    #         }, 500



    @restapi.method([(["/api/nc/fetch_all"], "POST")], auth="public")
    def fetch_all_nc(self):
        try:
            _logger.info("POST API for fetching all NC called")
            _logger.info("Received request at /api/nc/fetch_all")

            # Fetch all NCs
            ncs = request.env['manually.set.flag'].sudo().search([])

            # Prepare response data for all NCs
            nc_data = []
            for nc in ncs:
                _logger.debug("Processing nc ID: %s", nc.id)
                
                # Fetch all images for this NC - Fixed to return proper structure
                image_urls = []
                for img in nc.image_ids:
                    image_urls.append({
                        'id': img.id,
                        'url': f"/web/image/manually.set.flag.images/{img.id}/image",
                        'filename': img.filename or 'image.jpg'
                    })
                
                # Fetch all rectified images for this NC - Fixed to return proper structure
                rectified_image_urls = []
                for img in nc.rectified_image_ids:
                    rectified_image_urls.append({
                        'id': img.id,
                        'url': f"/web/image/manually.set.flag.rectified.images/{img.id}/rectified_image",
                        'filename': img.filename or 'rectified_image.jpg'
                    })

                approver_image_urls = []
                for img in nc.approver_image_ids:   
                    approver_image_urls.append({
                        'id': img.id,
                        'url': f"/web/image/manually.set.flag.close.images/{img.id}/approver_image",
                        'filename': img.filename or 'approver_image.jpg'
                    })

                approver_close_image_urls = []
                for img in nc.approver_close_image_ids:   
                    approver_close_image_urls.append({
                        'id': img.id,
                        'url': f"/web/image/manually.set.flag.approver.close.images/{img.id}/approver_image",
                        'filename': img.filename or 'approver_close_img.jpg'
                    })
                
                nc_data.append({
                    'seq_number': nc.seq_number,
                    'nc_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else None,
                    'project_info_name': nc.project_info_id.name if nc.project_info_id else '',
                    'project_tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'project_tower_name': nc.project_tower_id.name if nc.project_tower_id else '',
                    'project_floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'project_floor_name': nc.project_floor_id.name if nc.project_floor_id else '',
                    'project_flats_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'project_flats_name': nc.project_flats_id.name if nc.project_flats_id else '',
                    'project_activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'project_activity_name': nc.project_activity_id.name if nc.project_activity_id else '',
                    'project_act_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_act_type_name': nc.project_act_type_id.patn_id.name if nc.project_act_type_id else '',
                    'project_check_line_id': nc.project_check_line_id.id if nc.project_check_line_id else None,
                    'project_check_line_name': nc.project_check_line_id.checklist_id.name if nc.project_check_line_id and nc.project_check_line_id.checklist_id else '',
                    'custom_checklist_item': nc.custom_checklist_item or '',
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'project_responsible': nc.project_responsible.name if nc.project_responsible else '',
                    'project_responsible_id': nc.project_responsible.id if nc.project_responsible else None,
                    'description': nc.description or '',
                    'overall_remarks': nc.overall_remarks or '',
                    # 'approver_reject': nc.approver_reject or '',
                    'approver_remark': nc.approver_remark or '',
                    'flag_category': nc.flag_category or '',
                    'status': nc.status or '',
                    'images': image_urls,  
                    'rectified_images': rectified_image_urls, 
                    'image_count': len(image_urls),  
                    'rectified_image_count': len(rectified_image_urls),
                    'approver_reject_image': approver_image_urls,
                    'reject_image_count': len(approver_image_urls),
                    'approver_close_img': approver_close_image_urls,
                    'approver_close_img_count': len(approver_close_image_urls),
                    'close_image': image_urls,
#                     'rectified_image': (
#     f"/web/image/manually.set.flag/{nc.id}/image"
#     if nc.image else None
# ),
                })

            _logger.info(f"✅ Total NCs fetched: {len(ncs)}")

            return {
                'status': 'success',
                'total_count': len(ncs),
                'ncs': nc_data
            }, 200

        except Exception as e:
            _logger.error("❌ Error fetching NCs: %s", e, exc_info=True)
            return {
                'status': 'error',
                'message': 'Failed to fetch NCs.',
                'error_details': str(e)
            }, 500



    @restapi.method([(["/api/nc/fetch"], "POST")], auth="public")
    def fetch_nc_details(self):
        try:
            _logger.info("POST API for fetching NC details called")
            _logger.info("Received request at /api/nc/fetch")

            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called %s", data)
            nc_id = data.get('nc_id')

            if not nc_id:
                return {
                    'status': 'error',
                    'message': 'NC ID is required.'
                }, 400

            # Fetch the NC record by nc.id
            nc = request.env['manually.set.flag'].sudo().search([('id', '=', nc_id)], limit=1)

            if not nc:
                return {
                    'status': 'error',
                    'message': 'NC not found.'
                }, 404

            image_urls = []
            for img in nc.image_ids:
                image_urls.append({
                    'id': img.id,
                    'url': f"/web/image/manually.set.flag.images/{img.id}/image",
                    'filename': img.filename or 'image.jpg'
                })
            
            # Fetch all rectified images for this NC - Fixed to return proper structure
            rectified_image_urls = []
            for img in nc.rectified_image_ids:
                rectified_image_urls.append({
                    'id': img.id,
                    'url': f"/web/image/manually.set.flag.rectified.images/{img.id}/rectified_image",
                    'filename': img.filename or 'rectified_image.jpg'
                })

            approver_image_urls = []
            for img in nc.approver_image_ids:   
                approver_image_urls.append({
                    'id': img.id,
                    'url': f"/web/image/manually.set.flag.close.images/{img.id}/approver_image",
                    'filename': img.filename or 'approver_image.jpg'
                })

            approver_close_image_urls = []
            for img in nc.approver_close_image_ids:   
                approver_close_image_urls.append({
                    'id': img.id,
                    'url': f"/web/image/manually.set.flag.approver.close.images/{img.id}/approver_image",
                    'filename': img.filename or 'approver_close_img.jpg'
                })

            # Prepare the response data
            nc_data ={
                    'seq_number': nc.seq_number,
                    'nc_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else None,
                    'project_info_name': nc.project_info_id.name if nc.project_info_id else '',
                    'project_tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'project_tower_name': nc.project_tower_id.name if nc.project_tower_id else '',
                    'project_floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'project_floor_name': nc.project_floor_id.name if nc.project_floor_id else '',
                    'project_flats_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'project_flats_name': nc.project_flats_id.name if nc.project_flats_id else '',
                    'project_activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'project_activity_name': nc.project_activity_id.name if nc.project_activity_id else '',
                    'project_act_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_act_type_name': nc.project_act_type_id.patn_id.name if nc.project_act_type_id else '',
                    'project_check_line_id': nc.project_check_line_id.id if nc.project_check_line_id else None,
                    'project_check_line_name': nc.project_check_line_id.checklist_id.name if nc.project_check_line_id and nc.project_check_line_id.checklist_id else '',
                    'custom_checklist_item': nc.custom_checklist_item or '',
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'project_responsible': nc.project_responsible.name if nc.project_responsible else '',
                    'project_responsible_id': nc.project_responsible.id if nc.project_responsible else None,
                    'description': nc.description or '',
                    'overall_remarks': nc.overall_remarks or '',
                    # 'approver_reject': nc.approver_reject or '',
                    'approver_remark': nc.approver_remark or '',
                    'flag_category': nc.flag_category or '',
                    'status': nc.status or '',
                    'images': image_urls,  
                    'rectified_images': rectified_image_urls, 
                    'image_count': len(image_urls),  
                    'rectified_image_count': len(rectified_image_urls), 
                    'approver_reject_image': approver_image_urls,
                    'reject_image_count': len(approver_image_urls),
                    'close_image': image_urls,
                    'approver_close_img': approver_close_image_urls,
                    'approver_close_img_count': len(approver_close_image_urls),
#                     'rectified_image': (
#     f"/web/image/manually.set.flag/{nc.id}/image"
#     if nc.image else None
# ),
                }

            _logger.info("NC details fetched: %s", nc_data)

            return {
                'status': 'success',
                'nc': nc_data
            }, 200

        except Exception as e:
            _logger.error("Error fetching NC details: %s", e, exc_info=True)
            return {
                'status': 'error',
                'message': 'Failed to fetch NC details.',
                'error_details': str(e)
            }, 500


def _rotate_session(httprequest):
    if httprequest.session.rotate:
        root.session_store.delete(httprequest.session)
        httprequest.session.sid = root.session_store.generate_key()
        if httprequest.session.uid:
            httprequest.session.session_token = security.compute_session_token(
                httprequest.session, request.env
            )
        httprequest.session.modified = True


SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'phone', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang'}


def generateOTP():
    digits = "0123456789"
    OTP = ""
    for i in range(4):
        OTP += digits[int(math.floor(random.random() * 10))]
    return OTP
