import base64

import requests
from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)

try:
    from cachetools import LRUCache, cachedmethod
except ImportError:
    _logger.debug("Cannot import 'cachetools'.")


class MyController(http.Controller):

    @http.route('/get/activity/details', auth='public', methods=['POST'], csrf=False)
    def get_activity_details(self):
        # _logger.info("---------get_activity_details--------")
        data = json.loads(request.httprequest.data)
        # _logger.info("--------data--------",data)
        # _logger.info("---------projects--------,%s",(data))
        env = request.env
        activity_type_id = int(data['id'])
        activity_data = env['project.activity.type'].sudo(
        ).get_project_activity_details(activity_type_id)
        # _logger.info("---------Activity Data--------,%s",len(activity_data))
        return json.dumps({"status": "SUCCESS", "message": "Activity Data Fetch", "activity_data": activity_data})

    @http.route('/get/user/notifications', auth='public', methods=['POST'], csrf=False)
    def get_users_notification(self):
        # _logger.info("---------get_users_notificaton--------")
        data = json.loads(request.httprequest.data)
        env = request.env
        user_id = int(data['id'])
        Notifications = env['app.notification.log'].sudo(
        ).get_users_notification_details(user_id)
        # _logger.info("---------Notifications--------,%s",len(Notifications))
        return json.dumps({"status": "SUCCESS", "message": "Notification Fetch", "notification_data": Notifications})

    @http.route('/get/all/projects', auth='public', methods=['POST'], csrf=False)
    def get_all_projects(self):
        # _logger.info("---------get_all_projects--------")
        data = json.loads(request.httprequest.data)
        env = request.env
        # _logger.info((env))
        # _logger.info((data['id']))
        user_id = int(data['id'])
        projects = env['project.info'].sudo().get_all_projects_details(user_id)
        # _logger.info("---------projects--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS", "message": "Project Fetch", "project_data": projects})

    @http.route('/get/all/projects/towers/checklist', auth='public', methods=['POST'], csrf=False)
    def get_all_projects_towers_checklist(self):
        data = json.loads(request.httprequest.data)
        env = request.env
        # _logger.info((env))
        # _logger.info((data['id']))
        user_id = int(data['id'])
        # _logger.info("---------get_all_projects_towers_checklist--------")
        projects = env['project.info'].sudo(
        ).get_all_projects_towers_checklist_details(user_id)
        # _logger.info("-------get_all_projects_towers_checklist--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS", "message": "Project Fetch", "tower_info": projects})

    @http.route('/get/all/projects/flats/floors', auth='public', methods=['POST'], csrf=False)
    def get_all_projects_all_flats_floors(self):
        # _logger.info("---------get_all_projects_all_flats_floors--------")

        env = request.env
        data = json.loads(request.httprequest.data)
        env = request.env
        # _logger.info((env))
        # _logger.info((data['id']))
        user_id = int(data['id'])

        projects = env['project.info'].sudo(
        ).get_all_projects_all_flats_floors_details(user_id)
        # _logger.info("---------projects--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS", "message": "Tower info Fetch", "flat_floor_info": projects})

    ##### Need to shift all the above apis to session.py######

    @http.route('/onesignal/my_endpoint', auth='public', methods=['POST'], csrf=False)
    def my_endpoint(self, **kwargs):
        try:
            # Access POST data
            data = json.loads(request.httprequest.data)
            env = request.env
            _logger.info((env))
            _logger.info((data['id']))

            _logger.info((data['token']))
            _logger.info((data['player_id']))
            user_record = env['res.users'].sudo().browse(int(data['id']))
            if user_record:
                child_records = [(0, 0, {'player_id': data['player_id']})]
                user_record.sudo().write({'player_line_ids': child_records})
            # activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))

            # Process data (you can customize this part)
            result = {"success": True, "message": "Data received successfully"}
        except Exception as e:
            _logger.info(str(e))

            result = {"success": False, "message": str(e)}

        # Return the response as JSON
        return json.dumps(result)

    # API for activity list: listing all the activities

    @http.route('/activities', type='json', auth='public', methods=['POST'], csrf=False)
    def get_activities(self):
        _logger.info("Fetching all activities")
        try:
            activities = request.env['project.activity.name'].sudo().search([])
            activity_list = [{'name': act.name, 'activity_id': act.id}
                             for act in activities]
            # _logger.info("Successfully fetched activities: %s", activity_list)
            return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    # API for activity types {pre, post, during}

    @http.route('/activity/type_names', type='json', auth='public', methods=['POST'], csrf=False)
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

            # Fetch activity type names associated with the given activity
            activity_lines = request.env['project.activity.name.line'].sudo().search(
                [('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    # API for specific checklist items associated with activity type

    @http.route('/activity/checklist', type='json', auth='public', methods=['POST'], csrf=False)
    def get_activity_checklist(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            _logger.info("Received request data: %s", request.httprequest.data)
            data = json.loads(request.httprequest.data)
            _logger.info("Parsed JSON data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                _logger.warning(
                    "Activity Type Name ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity Type Name ID is required'}

            activity_type_name = request.env['project.activity.type.name'].sudo().browse(
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

    @http.route('/api/project/info', type='json', auth='public', methods=['POST'], csrf=False)
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

    @http.route('/api/tower/info', type='json', auth='public', methods=['POST'], csrf=False)
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
                return Response(
                    json.dumps(
                        {'status': 'FAILED', 'message': 'Please send Project ID'}),
                    content_type='application/json;charset=utf-8', status=400  # Bad Request
                )

            # Fetch tower records based on project_id
            tower_records = request.env['project.tower'].sudo().search(
                [('project_id', '=', project_id)])
            tower_data = [{'tower_id': tower.id, 'tower_name': tower.name}
                          for tower in tower_records]

            # Log fetched data
            # _logger.info("Fetched tower data: %s", tower_data)

            # Return success response
            return {'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'towers': tower_data}
        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return Response(
                json.dumps(
                    {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}),
                content_type='application/json;charset=utf-8', status=500
            )

    @http.route('/api/floor/info', type='json', auth='public', methods=['POST'], csrf=False)
    def get_floor_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            # Extract project_id
            tower_id = data.get('tower_id')

            # Validate project_id
            if not tower_id:
                _logger.warning("Tower ID is missing in the request")
                return Response(
                    json.dumps(
                        {'status': 'FAILED', 'message': 'Please send Tower ID'}),
                    content_type='application/json;charset=utf-8', status=400  # Bad Request
                )

            # Fetch tower records based on project_id
            floor_records = request.env['project.floors'].sudo().search(
                [('tower_id', '=', tower_id)])
            floor_data = [{'floor_id': floor.id, 'floor_name': floor.name}
                          for floor in floor_records]

            # Log fetched data
            # _logger.info("Fetched Floor data: %s", floor_data)

            # Return success response
            return {'status': 'SUCCESS', 'message': 'Floor Data Fetched', 'floors': floor_data}
        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return Response(
                json.dumps(
                    {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}),
                content_type='application/json;charset=utf-8', status=500
            )

    @http.route('/api/flat/info', type='json', auth='public', methods=['POST'], csrf=False)
    def get_flat_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            # Extract project_id
            tower_id = data.get('tower_id')

            # Validate project_id
            if not tower_id:
                _logger.warning("Tower ID is missing in the request")
                return Response(
                    json.dumps(
                        {'status': 'FAILED', 'message': 'Please send Tower ID'}),
                    content_type='application/json;charset=utf-8', status=400  # Bad Request
                )

            # Fetch tower records based on project_id
            flat_records = request.env['project.flats'].sudo().search(
                [('tower_id', '=', tower_id)])
            flat_data = [{'flat_id': flat.id, 'flat_name': flat.name}
                         for flat in flat_records]

            # Log fetched data
            _logger.info("Fetched Flat data: %s", flat_data)

            # Return success response
            return {'status': 'SUCCESS', 'message': 'Flat Data Fetched', 'flats': flat_data}
        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return Response(
                json.dumps(
                    {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}),
                content_type='application/json;charset=utf-8', status=500
            )

    @http.route('/api/activities/info', type='json', auth='public', methods=['POST'], csrf=False)
    def get_activities_info(self):
        _logger.info("Fetching activities with filters")

        try:
            # Extract JSON data from request
            data = json.loads(request.httprequest.data.decode('utf-8')) or {}
            _logger.info("Received request data: %s", data)

            domain = []

            # Extract single ID values using data.get()
            floor_id = data.get("floor_id")
            flat_id = data.get("flat_id")
            tower_id = data.get("tower_id")
            project_id = data.get("project_id")

            # Apply filters dynamically if values are provided
            if floor_id:
                domain.append(('floor_id', '=', floor_id))
            if flat_id:
                domain.append(('flat_id', '=', flat_id))
            if tower_id:
                domain.append(('tower_id', '=', tower_id))
            if project_id:
                domain.append(('project_id', '=', project_id))

            _logger.info("Applying domain filters: %s", domain)

            # Fetch activities based on the domain filters
            activities = request.env['project.activity'].sudo().search(domain)

            # Prepare response data
            activity_list = [
                {
                    'name': act.project_activity_name_id.name,
                    'activity_id': act.project_activity_name_id.id,
                    'floor_id': act.floor_id.id if act.floor_id else None,
                    'flat_id': act.flat_id.id if act.flat_id else None,
                    'tower_id': act.tower_id.id if act.tower_id else None,
                    'project_id': act.project_id.id if act.project_id else None
                }
                for act in activities
            ]

            _logger.info("Successfully fetched activities: %s", activity_list)

            return {
                'status': 'SUCCESS',
                'message': 'Activities fetched successfully',
                'data': activity_list
            }

        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {
                'status': 'FAILED',
                'message': 'Error fetching activities',
                'error': str(e)
            }

    @http.route('/api/users/list', type='json', auth='public', methods=['POST'], csrf=False)
    def get_project_responsibles(self):
        try:
            partners = request.env['res.users'].sudo().search([])
            partner_data = [
                {'project_responsible_id': partner.id, 'name': partner.name}
                for partner in partners
            ]
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

    # API for activity types {pre, post, during}

    @http.route('/api/activity/type/info', type='json', auth='public', methods=['POST'], csrf=False)
    def get_activity_type_info(self):
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

            # Fetch activity type names associated with the given activity
            activity_lines = request.env['project.activity.name.line'].sudo().search(
                [('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    # API for specific checklist items associated with activity type

    @http.route('/api/activity/checklist/info', type='json', auth='public', methods=['POST'], csrf=False)
    def get_activity_checklist_info(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            _logger.info("Received request data: %s", request.httprequest.data)
            data = json.loads(request.httprequest.data)
            _logger.info("Parsed JSON data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                _logger.warning(
                    "Activity Type Name ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity Type Name ID is required'}

            activity_type_name = request.env['project.activity.type.name'].sudo().browse(
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

    @http.route('/api/nc/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC creation called")
            _logger.info("Received JSON request: %s", data)

            _logger.info("Extracted activity_id: %s", data.get('activity_id'))
            # Extract required fields
            project_info_id = data.get('project_id')
            project_tower_id = data.get('tower_id')
            project_floor_id = data.get('floor_id')
            project_flats_id = data.get('flat_id')
            project_activity_id = data.get('activity_id')
            _logger.info("Extracted activity_id: %s", project_activity_id)

            project_act_type_id = data.get('activity_type_id')
            project_check_line_id = data.get('id')
            custom_checklist_item = data.get('custom_checklist_item')
            description = data.get('description')
            rectified_image = data.get('rectified_image')
            flag_category = data.get('flag_category')
            project_create_date = data.get('project_create_date')
            project_responsible = data.get('project_responsible_id')
            status = data.get('status')

            # Handle Image Upload

            image_data = None
            rectified_image_data = rectified_image

            if rectified_image_data:
                try:
                    image_data = rectified_image_data.split(',')[1]
                    decoded_image = base64.b64decode(image_data)

                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': 'rectified_image.jpg',
                        'type': 'binary',
                        'datas': base64.b64encode(decoded_image),
                        'res_model': 'manually.set.flag',
                        'res_id': nc.id,
                    })
                except Exception as e:
                    _logger.error(f"Error decoding image: {str(e)}")

            # Create NC record
            nc_values = {
                'project_info_id': project_info_id,
                'project_tower_id': project_tower_id,
                'project_floor_id': project_floor_id,
                'project_flats_id': project_flats_id,
                'project_activity_id': project_activity_id,
                'project_act_type_id': project_act_type_id,
                'project_check_line_id': project_check_line_id,
                'description': description,
                'rectified_image': image_data,
                'flag_category': flag_category,
                'project_create_date': project_create_date,
                'project_responsible': project_responsible,
                'status': status,
            }

            if custom_checklist_item:
                nc_values['custom_checklist_item'] = custom_checklist_item

            nc_values.pop('seq_number', None)
            nc_values['seq_number'] = request.env['ir.sequence'].sudo(
            ).next_by_code('manually.set.flag') or _('New')  # type: ignore

            nc = request.env['manually.set.flag'].sudo().create(nc_values)
            _logger.info("NC created successfully with ID: %s", nc.id)

            # Prepare response data
            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC created successfully.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'project_id': nc.project_info_id.id,
                    'tower_id': nc.project_tower_id.id,
                    'floor_id': nc.project_floor_id.id,
                    'flat_id': nc.project_flats_id.id,
                    'activity_id': nc.project_activity_id.id,
                    'activity_type_id': nc.project_act_type_id.id,
                    'id': nc.project_check_line_id.id,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'rectified_image': rectified_image,
                    'project_create_date': nc.project_create_date,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'custom_checklist': nc.custom_checklist_item
                }
            }

            # Send Notification to Project Responsible
            if nc.project_responsible:
                notification_status = self.send_notification(nc)
                response_data['notification_status'] = notification_status

            return response_data, 201  # HTTP 201 Created

        except Exception as e:
            _logger.error("Error creating NC: %s", e)
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500  # HTTP 500 Internal Server Error

    def send_notification(self, nc):
        """ Sends push notification to the responsible person """
        if not nc.project_responsible:
            return {'error': 'No responsible person assigned'}

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        seq_no = nc.seq_number
        # Get current user's name
        current_user_name = request.env.user.name if request.env.user else 'Unknown User'

        # Update the message
        message = f"{current_user_name} has created a {flag_category} for {project_name}/{tower_name}."
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

# 27-03
    # @http.route('/api/nc/create', type='json', auth='public', methods=['POST'], csrf=False)
    # def create_nc(self):
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("POST API for NC creation called")
    #         _logger.info("Received JSON request: %s", data)

    #         # Extract required fields
    #         project_info_id = data.get('project_id')
    #         project_tower_id = data.get('tower_id')
    #         project_floor_id = data.get('floor_id')
    #         project_flats_id = data.get('flat_id')
    #         project_activity_id = data.get('activity_id')
    #         project_act_type_id = data.get('activity_type_id')
    #         project_check_line_id = data.get('id')
    #         description = data.get('description')
    #         rectified_image = data.get('rectified_image')
    #         flag_category = data.get('flag_category')
    #         project_create_date = data.get('project_create_date')
    #         project_responsible = data.get('project_responsible_id')
    #         status = data.get('status')

    #         # Decode the base64 image
    #         image_data = None
    #         if rectified_image:
    #             try:
    #                 image_data = rectified_image.split(',')[1]
    #                 decoded_image = base64.b64decode(image_data)

    #                 attachment = request.env['ir.attachment'].sudo().create({
    #                     'name': 'rectified_image.jpg',
    #                     'type': 'binary',
    #                     'datas': base64.b64encode(decoded_image),
    #                     'res_model': 'manually.set.flag',
    #                 })
    #             except Exception as e:
    #                 _logger.error(f"Error decoding image: {str(e)}")

    #         # Create the NC record
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

    #         nc = self.env['manually.set.flag'].sudo().create(
    #             nc_values)  # Create NC record
    #         _logger.info(f"✅ NC Created: ID {nc.id}")

    #         # Fetch responsible user
    #         project_responsible = self.env['res.users'].browse(
    #             data.get('project_responsible_id'))

    #         # 🔥 Ensure the function is called
    #         self.env['app.notification.log'].sudo().create_nc_notification(nc,
    #                                                                        project_responsible)

    #         return {
    #             'status': 'success',
    #             'nc_id': nc.id,
    #             'message': 'NC created successfully.',
    #             'nc_data': {
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
    #                 'project_responsible': nc.project_responsible.id if nc.project_responsible else None
    #             }
    #         }, 201  # HTTP 201 Created

    #     except Exception as e:
    #         _logger.error("Error creating NC: %s", e)
    #         return {
    #             'status': 'error',
    #             'message': f'Failed to create NC: {str(e)}'
    #         }, 500  # HTTP 500 Internal Server Error

    # def create_nc_notification(self, nc, project_responsible):
    #     """Creates a notification for NC in app.notification.log."""
    #     if not project_responsible:
    #         _logger.warning("No responsible user found for NC notification.")
    #         return

    #     notification_vals = {
    #         'res_user_id': project_responsible,
    #         'status': 'nc',
    #         'title': 'New NC Created',
    #         # 'notification_dt': fields.Datetime.now(),
    #         'detail_line': f"A new NC has been created for project {nc.project_info_id.name}.",
    #         'seq_no': nc.id,
    #         'hide_notification': False,
    #     }

    #     notification = request.env['app.notification.log'].sudo().create(
    #         notification_vals)
    #     _logger.info(f"NC Notification Created: {notification.id}")

    #     # Send Push Notification (Optional)
    #     player_id, _ = request.env['res.users'].get_player_id(
    #         project_responsible)
    #     if player_id:
    #         notification_title = "New NC Created"
    #         notification_message = f"User {request.env.user.name} has created a flag for this project."

    #         request.env['app.notification'].send_push_notification(
    #             title=notification_title,
    #             player_ids=[player_id],
    #             message=notification_message,
    #             user_ids=[project_responsible],
    #             seq_no=nc.id,
    #             insp_value='NC',
    #             obj=nc
    #         )

    @http.route('/api/nc/fetch_all', type='json', auth='public', methods=['POST'], csrf=False)
    def fetch_all_nc(self):
        try:
            _logger.info("POST API for fetching all NC called")
            _logger.info("Received request at /api/nc/fetch_all")

            # Fetch all tasks
            ncs = request.env['manually.set.flag'].sudo().search([])

            # Prepare response data for all tasks
            nc_data = []
            for nc in ncs:
                _logger.debug("Processing nc ID: %s", nc.id)
                nc_data.append({
                    'nc_id': nc.id,
                    'seq_number': nc.seq_number,
                    'project_info_id': nc.project_info_id.id,
                    'project_info_name': nc.project_info_id.name,
                    'project_tower_id': nc.project_tower_id.id,
                    'project_tower_name': nc.project_tower_id.name,
                    'project_floor_id': nc.project_floor_id.id,
                    'project_floor_name': nc.project_floor_id.name,
                    'project_flats_id': nc.project_flats_id.id,
                    'project_flats_name': nc.project_flats_id.name,

                    'project_activity_id': nc.project_activity_id.id,
                    'project_activity_name': nc.project_activity_id.name,

                    'project_act_type_id': nc.project_act_type_id.id,
                    'project_act_type_name': nc.project_act_type_id.name,

                    'project_check_line_id': nc.project_check_line_id.id,
                    'project_check_line_name': nc.project_check_line_id.checklist_template_id.name,
                    'custom_checklist_item': nc.custom_checklist_item,
                    'project_create_date': nc.project_create_date,
                    'project_responsible': nc.project_responsible.name,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'rectified_image': nc.rectified_image,
                })

            _logger.info("Total ncs fetched: %s", len(ncs))

            return {
                'status': 'success',
                'ncs': nc_data
            }, 200

        except Exception as e:
            _logger.error("Error fetching ncs: %s", e, exc_info=True)
            return {
                'status': 'error',
                'message': 'Failed to fetch ncs.',
                'error_details': str(e)
            }, 500

    @http.route('/api/nc/close', type='json', auth='public', methods=['POST'], csrf=False)
    def close_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called")

            nc_id = data.get('nc_id')
            status = data.get('status')
            image = data.get('image')
            description = data.get('description')

            if not nc_id or status != 'close':
                return {'status': 'error', 'message': 'Invalid NC ID or status'}, 400

            image_data = None
            rimage_data = image

            if rimage_data:
                try:
                    image_data = rimage_data.split(',')[1]
                    decoded_image = base64.b64decode(
                        image_data)

                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': 'image.jpg',
                        'type': 'binary',
                        'datas': base64.b64encode(decoded_image),
                        'res_model': 'manually.set.flag',
                        'res_id': nc.id,
                    })
                except Exception as e:
                    _logger.error(f"Error decoding image: {str(e)}")

            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

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
                'status': 'close',
                'description': description,
                'image': image_data,
            })

            _logger.info("NC status updated to 'close' with ID: %s", nc.id)

            # Send notification to project responsible
            if nc.project_responsible:
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
                    'flag_category': nc.flag_category,
                    'rectified_image': nc.rectified_image,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'image': image,
                },
                'notification_status': notification_status if nc.project_responsible else None
            }

            return response_data, 200

        except Exception as e:
            _logger.error("Error closing NC: %s", e)
            return {'status': 'error', 'message': f'Failed to close NC: {str(e)}'}, 500

    def send_close_notification(self, nc):
        if not nc.project_responsible and not request.env.user:
            return {'error': 'No recipient found for notification'}

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        seq_no = nc.seq_number
        current_user = request.env.user  # Get the user who is closing the NC
        current_user_name = current_user.name if current_user else 'Unknown User'

        message = f"{current_user_name} has closed the {flag_category} for {project_name}/{tower_name}."
        title = message

        # Get player IDs for both project responsible & closing user
        player_ids = []

        # Project Responsible
        if nc.project_responsible:
            project_responsible_player, _ = request.env['res.users'].sudo(
            ).get_player_id(nc.project_responsible.id)
            if project_responsible_player:
                player_ids.append(project_responsible_player)

        # User who closed the NC
        if current_user:
            closing_user_player, _ = request.env['res.users'].sudo(
            ).get_player_id(current_user.id)
            if closing_user_player:
                player_ids.append(closing_user_player)

        if not player_ids:
            return {'error': 'No push notification IDs found for recipients'}

        app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
        rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

        data = {
            "app_id": app_id,
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        data_json = json.dumps(data)
        url = "https://onesignal.com/api/v1/notifications"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {rest_api_key}"
        }

        response = requests.post(url, data=data_json, headers=headers)
        status = 'sent' if response.status_code == 200 else 'failed'

        # Log notification for both users
        for user_id in [nc.project_responsible.id, current_user.id]:
            if user_id:
                request.env['app.notification.log'].sudo().create({
                    'title': title if status == 'sent' else f"{title} (Failed)",
                    'message': message,
                    'res_user_id': user_id,
                    'status': status,
                    'seq_no': seq_no,
                    'table_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
                })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}

    # def create_nc(self):
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("POST API for NC creation called")
    #         _logger.info("Received JSON request: %s", data)

    #         # Extract required fields
    #         project_info_id = data.get('project_id')
    #         project_tower_id = data.get('tower_id')
    #         project_floor_id = data.get('floor_id')
    #         project_flats_id = data.get('flat_id')
    #         project_activity_id = data.get('activity_id')
    #         project_act_type_id = data.get('activity_type_id')
    #         project_check_line_id = data.get('id')
    #         description = data.get('description')
    #         rectified_image = data.get('rectified_image')
    #         flag_category = data.get('flag_category')
    #         project_create_date = data.get('project_create_date')
    #         project_responsible = data.get('project_responsible_id')
    #         # date, project_responsible

    #         # Decode the base64 image

    #         image_data = None
    #         rectified_image_data = rectified_image

    #         if rectified_image_data:
    #             try:
    #                 image_data = rectified_image_data.split(',')[1]
    #                 decoded_image = base64.b64decode(
    #                     image_data)

    #                 attachment = self.env['ir.attachment'].sudo().create({
    #                     'name': 'rectified_image.jpg',
    #                     'type': 'binary',
    #                     'datas': base64.b64encode(decoded_image),
    #                     'res_model': 'manually.set.flag',
    #                     'res_id': nc.id,
    #                 })
    #             except Exception as e:
    #                 _logger.error(f"Error decoding image: {str(e)}")

    #         # Create a new nc
    #         nc = request.env['manually.set.flag'].sudo().create({
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
    #         })
    #         _logger.info("NC created with values: %s", nc.id)

    #         _logger.info("NC created successfully with ID: %s", nc.id)

    #         response_data = {
    #             'status': 'success',
    #             'nc_id': nc.id,
    #             'message': 'NC created successfully.',
    #             'nc_data': {
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
    #                 'project_responsible': nc.project_responsible
    #             }
    #         }
    #         _logger.info("Response data to be returned: %s", response_data)

    #         return response_data, 201  # HTTP 201 Created

    #     except Exception as e:
    #         _logger.error("Error creating task: %s", e)
    #         return {
    #             'status': 'error',
    #             'message': f'Failed to create task: {str(e)}'
    #         }, 500   # HTTP 500 Internal Server Error
