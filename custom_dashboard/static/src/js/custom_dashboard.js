console.log("starting");
odoo.define('custom_dashboard.DashboardRewrite', function (require) {
"use strict";
console.log("started");
const ActionMenus = require('web.ActionMenus');
const ComparisonMenu = require('web.ComparisonMenu');
const ActionModel = require("web.ActionModel");
const FavoriteMenu = require('web.FavoriteMenu');
const FilterMenu = require('web.FilterMenu');
const GroupByMenu = require('web.GroupByMenu');
const Pager = require('web.Pager');
const SearchBar = require('web.SearchBar');
const { useModel } = require('web.Model');
const { Component, hooks } = owl;

var concurrency = require('web.concurrency');
var config = require('web.config');
var field_utils = require('web.field_utils');
var time = require('web.time');
var utils = require('web.utils');
var AbstractAction = require('web.AbstractAction');
var ajax = require('web.ajax');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var core = require('web.core');
var rpc = require('web.rpc');
var session = require('web.session');
var web_client = require('web.web_client');
var abstractView = require('web.AbstractView');
var _t = core._t;
var QWeb = core.qweb;

const { useRef, useSubEnv } = owl;

var Dashboard = AbstractAction.extend({
    template: 'DashboardMain',
    cssLibs: [
        '/custom_dashboard/static/src/css/lib/nv.d3.css'
    ],
    jsLibs: [
        '/custom_dashboard/static/src/js/lib/d3.min.js'
    ],

    // Click Onchange Events
    events: {
        'click #all_project': 'all_project_count',
        'click #all_towers': 'all_tower_count',
        'click #all_floors': 'all_floor_count',
        'click #all_flats': 'all_flat_count',
        'change #project_type': 'onProjectTypeChange',
        'change #project_details': 'fetchTowers',
        'change #section_select': 'onchange_render_section_wise',
        'change #nc_yc_select': 'onchange_render_section_wise_nc',
        'change #pending_complete_select': 'onchange_render_section_wise_pending_complete',
        'change #tower_type': 'onTowerTypeChange',
        'change #floor_type': 'onchange_render_floor_wise',
        'change #flat_type': 'onchange_render_flat_wise',
    },

    init: function(parent, context) {
        this._super(parent, context);
        this.dashboards_templates = ['DashboardCountDiv', 'Dashboard'];
    },

    onPendingCompleteChange: function () {
            this.pending_complete_select();
        },
    onProjectTypeChange: function () {
            this.onchange_render_project_wise();
            this.onchange_render_section_wise_nc();
            this.fetchTowers();
            this.fetchTowersProject();
            this.render_bar_chart_c_m_a();
            this.render_pending_bar_chart_c_m_a();
            this.render_bar_chart();
        },

    onTowerTypeChange: function () {
            this.onchange_render_tower_wise();
            this.onchange_render_section_wise_nc();
            this.fetchTowers();
            this.fetchTowersProject();
            this.render_bar_chart_c_m_a();
            this.render_pending_bar_chart_c_m_a();
            this.render_bar_chart_tower();
            this.render_bar_chart();
        },

    // always page refresh
    willStart: function() {
        var self = this;
        return this._super().then(function() {
            // Call showSection with 'project' to set the default section
//            self.showSection('tower');

            // Fetch data after setting the default section
            var def1 = self._rpc({
                model: "project.info",
                method: "get_all_project_info_count",
            }).then(function(res) {
                self.total_project = res['total_project'];
            });

            var def2 = self._rpc({
                model: 'project.tower',
                method: 'get_all_project_towers'
            }).then(function(res) {
                self.total_tower = res['total_tower'];
            });

            var def3 = self._rpc({
                model: 'project.floors',
                method: 'get_all_project_floors'
            }).then(function(res) {
                self.total_floors = res['total_floors'];
            });

            var def4 = self._rpc({
                model: 'project.flats',
                method: 'get_all_project_flats'
            }).then(function(res) {
                self.total_flats = res['total_flats'];
            });

            var def5 = self._rpc({
                model: 'project.info',
                method: 'get_all_project_nc_count'
            }).then(function(res) {
                self.total_nc_count = res['total_nc_count'];
            });

            var def6 = self._rpc({
                model: 'project.info',
                method: 'get_all_project_nc_count'
            }).then(function(res) {
                self.total_green_flag_count = res['total_green_flag_count'];
            });

            var def7 = self._rpc({
                model: 'project.info',
                method: 'get_all_project_nc_count'
            }).then(function(res) {
                self.total_orange_flag_count = res['total_orange_flag_count'];
            });

            var def8 = self._rpc({
                model: 'project.info',
                method: 'get_all_project_nc_count'
            }).then(function(res) {
                self.total_yellow_flag_count = res['total_yellow_flag_count'];
            });

            var def9 = self._rpc({
                model: 'project.info',
                method: 'get_all_project_nc_count'
            }).then(function(res) {
                self.total_red_flag_count = res['total_red_flag_count'];
            });

            return $.when(def1, def2, def3, def4, def5, def6, def7, def8, def9);
        });
    },

    //Start
    start: function() {
        var self = this;
        console.log('--------Start-------')
        this.set("title", 'Dashboard');
        return this._super().then(function() {
            self.update_cp();
            self.onchange_render_project_wise();
            self.onchange_render_section_wise_nc();
//            self.onchange_render_section_project_type();
            self.onchange_render_section_wise_pending_complete();
            self.onchange_render_section_wise();
            self.fetchProject();
            self.fetchTowers();
            self.fetchFloors();
            self.fetchFlats();
            self.render_dashboards();
//            self.render_graphs();
//            self.render_bar_chart_c_m_a();
//            self.render_pending_graphs_c_m_a();
//            self.render_graphs_tower();
            self.render_graphs_floor();
            self.render_graphs_flat();
            self.$el.parent().addClass('oe_background_grey');
        });
    },

    update_cp: function() {
        var self = this;
    },

    // Event Start
    all_project_count: function(ev){
        var self = this;
        ev.stopPropagation();
        ev.preventDefault();
        var option = $(ev.target).val();
//        var option = $(events.target).val();
        this.do_action({
            name: _t("Project Info"),
            type: 'ir.actions.act_window',
            res_model: 'project.info',
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'],[false, 'list'],[false, 'form']],
            target: 'current'
        },)
    },

    all_tower_count: function(ev){
        var self = this;
        ev.stopPropagation();
        ev.preventDefault();
        this.do_action({
            name: _t("Project Tower"),
            type: 'ir.actions.act_window',
            res_model: 'project.tower',
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'],[false, 'list'],[false, 'form']],
            target: 'current'
        },)
    },

    all_floor_count: function(ev){
        var self = this;
        ev.stopPropagation();
        ev.preventDefault();
        this.do_action({
            name: _t("Project Floor"),
            type: 'ir.actions.act_window',
            res_model: 'project.floors',
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'],[false, 'list'],[false, 'form']],
            target: 'current'
        },)
    },

    all_flat_count: function(ev){
        var self = this;
        ev.stopPropagation();
        ev.preventDefault();
        this.do_action({
            name: _t("Project Flat"),
            type: 'ir.actions.act_window',
            res_model: 'project.flats',
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'],[false, 'list'],[false, 'form']],
            target: 'current'
        },)
    },

    fetch_data: function(){
        var self = this;
        var def1 = this._rpc({
            model: 'project.info',
            method: 'get_all_project_info_count'
        }).then(function(result){
            self.total_project = result['total_project']
        });
        var def2 = this._rpc({
            model: 'project.tower',
            method: 'get_all_project_towers'
        }).then(function(result){
            self.total_tower = result['total_tower']
        });
        var def3 = this._rpc({
            model: 'project.floors',
            method: 'get_all_project_floors'
        }).then(function(result){
            self.total_floors = result['total_floors']
        });
        var def4 = this._rpc({
            model: 'project.flats',
            method: 'get_all_project_flats'
        }).then(function(result){
            self.total_flats = result['total_flats']
        });
        var def5 = this._rpc({
            model: 'project.info',
            method: 'get_all_project_nc_count'
        }).then(function(result){
            self.total_nc_count = result['total_nc_count']
        });
        var def6 = this._rpc({
            model: 'project.info',
            method: 'get_all_project_nc_count'
        }).then(function(result){
            self.total_green_flag_count = result['total_green_flag_count']
        });
        var def7 = this._rpc({
            model: 'project.info',
            method: 'get_all_project_nc_count'
        }).then(function(result){
            self.total_orange_flag_count = result['total_orange_flag_count']
        });
        var def8 = this._rpc({
            model: 'project.info',
            method: 'get_all_project_nc_count'
        }).then(function(result){
            self.total_yellow_flag_count = result['total_yellow_flag_count']
        });
        var def9 = this._rpc({
            model: 'project.info',
            method: 'get_all_project_nc_count'
        }).then(function(result){
            self.total_red_flag_count = result['total_red_flag_count']
        });
        return $.when(def1, def2, def3, def4, def5, def6, def7, def8, def9);
    },

    render_dashboards: function(){
        var self = this;
        _.each(this.dashboards_templates, function(template){
            self.$('.o_hr_dashboard').append(QWeb.render(template, {widget: self}));
        });
    },

//    selected value in dashboard according to Project Tower Flat Floor

    fetchProject: function () {
        var self = this;
        this._rpc({
            model: 'project.info',
            method: 'get_project_names',
        }).then(function (data) {
            self.projects = data;
            self.renderProject();
        });
    },

//    onProjectChange: function () {
//        var selectedValue = this.$('#project_type').val();
//        if (selectedValue) {
//            // Call a method or perform an action when tower selection changes
//            this.trigger_up('project_selection_changed', {project_id: selectedValue});
//        }
//    },

    renderProject: function () {
        var $select = this.$('#project_type');
        $select.empty().append($('<option>', {
            value: '',
            text: 'Select Project'
        }));
        _.each(this.projects, function (project) {
            $select.append($('<option>', {
                value: project.id,
                text: project.name
            }));
        });
    },

    fetchTowers: function () {
        var self = this;
        var project_detailsValue = this.$('#project_details').val();
        var projectValue = this.$('#project_type').val();
        var towerValue = this.$('#tower_type').val();
        this._rpc({
            model: 'project.tower',
            method: 'get_tower_names',
            args: [projectValue, project_detailsValue],
        }).then(function (data) {
            self.towers = data;
            self.renderTowers();
        });
    },

    fetchTowersProject: function() {
        var selectedValue = this.$('#nc_yc_select').val();
        var projectValue = this.$('#project_type').val();
        var towerValue = this.$('#tower_type').val();
        console.log(projectValue, '--------selectedValue-----towerValue-', towerValue);
        const project_section_div = this.$('#project_section_div');
        const tower_section_div = this.$('#tower_section_div');
        if (!project_section_div || !tower_section_div) {
            console.error("One or more sections are missing in the DOM");
            return;
        }
        function showSection(section) {
            project_section_div.addClass('d-none');
            tower_section_div.addClass('d-none');
            console.error("=========Section projectValue===============", section);
            if (section >= 1 && section <= 500)
//            (section !== 'Select Tower')
            {
                console.error("=========Section If===============", section);
                project_section_div.addClass('d-none');
                tower_section_div.removeClass('d-none');
            } else
              {
                console.error("=========Section Else===============", section);
                tower_section_div.addClass('d-none');
                project_section_div.removeClass('d-none');
            }
        }

        showSection(towerValue);
    },

    renderTowers: function () {
    var $select = this.$('#tower_type');
    var currentValue = $select.val(); // 🔹 Remember current value

    $select.empty().append($('<option>', {
        value: '',
        text: 'Select Tower'
    }));

    _.each(this.towers, function (tower) {
        $select.append($('<option>', {
            value: tower.id,
            text: tower.name
        }));
    });

    $select.val(currentValue); // 🔹 Re-set selected value (if it still exists)
    },

    // renderTowers: function () {
    //     var $select = this.$('#tower_type');
    //     $select.empty().append($('<option>', {
    //         value: '',
    //         text: 'Select Tower'
    //     }));
    //     _.each(this.towers, function (tower) {
    //         $select.append($('<option>', {
    //             value: tower.id,
    //             text: tower.name
    //         }));
    //     });
    // },

//    onTowerChange: function () {
//        var selectedValue = this.$('#tower_type').val();
//        if (selectedValue) {
//            // Call a method or perform an action when tower selection changes
//            this.trigger_up('tower_selection_changed', {project_id: selectedValue});
//        }
//    },

    fetchFloors: function () {
        var self = this;
        this._rpc({
            model: 'project.floors',
            method: 'get_floors_names',
        }).then(function (data) {
            self.floors = data;
            self.renderFloors();
        });
    },

    renderFloors: function () {
        var $select = this.$('#floor_type');
        $select.empty().append($('<option>', {
            value: '',
            text: 'Select Floors'
        }));
        _.each(this.floors, function (floor) {
            $select.append($('<option>', {
                value: floor.id,
                text: floor.name
            }));
        });
    },

//    onFloorsChange: function () {
//        var selectedValue = this.$('#floor_type').val();
//        if (selectedValue) {
//            // Call a method or perform an action when tower selection changes
//            this.trigger_up('floor_selection_changed', {floor_id: selectedValue});
//        }
//    },

    fetchFlats: function () {
//        var $project = this.$('#project_type');
        var self = this;
        this._rpc({
            model: 'project.flats',
            method: 'get_flats_names',
        }).then(function (data) {
            self.flats = data;
            self.renderFlats();
        });
    },

    renderFlats: function () {
        var $select = this.$('#flat_type');
        $select.empty().append($('<option>', {
            value: '',
            text: 'Select Flats'
        }));
        _.each(this.flats, function (flat) {
            $select.append($('<option>', {
                value: flat.id,
                text: flat.name
            }));
        });
    },

    onFlatsChange: function () {
        var selectedValue = this.$('#flat_type').val();
        if (selectedValue) {
            // Call a method or perform an action when tower selection changes
            this.trigger_up('flat_selection_changed', {flat_id: selectedValue});
        }
    },


    onchange_render_section_wise: function() {
        var selectedValue = this.$('#section_select').val();
        var PValue = this.$('#project_type').val();
        var FValue = this.$('#floor_type').val();
        var TValue = this.$('#tower_type').val();
        var flatValue = this.$('#flat_type').val();
        console.log('--------selectedValue------', selectedValue, PValue);

        // Move these inside the function to ensure they are always retrieved when needed
        const projectSection = this.$('#project_section');
        const towerSection = this.$('#tower_section');
        const floorSection = this.$('#floor_section');
        const flatSection = this.$('#flat_section');
        const projectSectionDiv = document.getElementById('project_section_div');
        const towerSectionDiv = document.getElementById('tower_section_div');
        const floorSectionDiv = document.getElementById('floor_section_div');
        const flatSectionDiv = document.getElementById('flat_section_div');

        if (!projectSection || !towerSection || !floorSection || !flatSection || !projectSectionDiv || !towerSectionDiv || !floorSectionDiv || !flatSectionDiv) {
            console.error("One or more sections are missing in the DOM");
            return;
        }

        function showSection(section, PValue) {
            projectSection.addClass('d-none');
            towerSection.addClass('d-none');
            floorSection.addClass('d-none');
            flatSection.addClass('d-none');
            projectSectionDiv.classList.add('d-none');
            towerSectionDiv.classList.add('d-none');
            floorSectionDiv.classList.add('d-none');
            flatSectionDiv.classList.add('d-none');

            if (section === 'project') {
                projectSection.removeClass('d-none');
                projectSectionDiv.classList.remove('d-none');
    //            if (PValue === 'Select Project') {
    //                projectSectionDiv.classList.remove('d-none');
    //            }
            } else if (section === 'tower') {
                towerSection.removeClass('d-none');
                towerSectionDiv.classList.remove('d-none');
    //            if (TValue === 'Select Tower') {
    //                towerSectionDiv.classList.remove('d-none');
    //            }
            } else if (section === 'floor') {
                floorSection.removeClass('d-none');
                floorSectionDiv.classList.remove('d-none');
    //            if (FValue === 'Select Floor') {
    //                floorSectionDiv.classList.remove('d-none');
    //            }
            } else if (section === 'flat') {
                flatSection.removeClass('d-none');
                flatSectionDiv.classList.remove('d-none');
    //            if (flatValue === 'Select Flat') {
    //                flatSectionDiv.classList.remove('d-none');
    //            }
            }
        }
        showSection(selectedValue, PValue);
    },

//    Project wise count of NC / YC / OC / RC / GC
    onchange_render_section_wise_nc: function() {
        var selectedValue = this.$('#nc_yc_select').val();
        var TValue = this.$('#tower_type').val();
        console.log('--------selectedValue------', selectedValue,);

        // Move these inside the function to ensure they are always retrieved when needed
        const projectSection = this.$('#project_nc');
        const towerSection = this.$('#tower_nc');
        const floorSection = this.$('#floor_nc');
        const flatSection = this.$('#flat_nc');

        if (!projectSection || !towerSection || !floorSection || !flatSection) {
            console.error("One or more sections are missing in the DOM");
            return;
        }

        function showSection(section) {
            projectSection.addClass('d-none');
            towerSection.addClass('d-none');
            floorSection.addClass('d-none');
            flatSection.addClass('d-none');

//            if (section === 'project') {
            if (section >= 1 && section <= 500) {
                projectSection.addClass('d-none');
                towerSection.removeClass('d-none');
            } else
                {
                towerSection.addClass('d-none');
                projectSection.removeClass('d-none');
            }
//            else if (section === 'floor') {
//                floorSection.removeClass('d-none');
//            } else if (section === 'flat') {
//                flatSection.removeClass('d-none');
//            }
        }
//        showSection(selectedValue);
        showSection(TValue);
    },

//  Checker Maker
    onchange_render_section_wise_pending_complete: function() {
        var selectedValue = this.$('#pending_complete_select').val();
        console.log('--------selectedValue------', selectedValue,);

        // Move these inside the function to ensure they are always retrieved when needed
        const pendingSection = this.$('#pending');
        const completeSection = this.$('#complete');

        if (!pendingSection || !completeSection) {
            console.error("One or more sections are missing in the DOM");
            return;
        }

        function showSection(section) {
            pendingSection.addClass('d-none');
            completeSection.addClass('d-none');

            if (section === 'pending') {
//                pendingSection.removeClass('d-none');
                completeSection.removeClass('d-none');
            } else if (section === 'complete') {
                pendingSection.removeClass('d-none');
            }
        }
        showSection(selectedValue);
    },
//    onchange_render_section_project_type: function() {
//        var selectedValue = this.$('#project_type').val();
//        var towerValue = this.$('#tower_type').val();
//        console.log(selectedValue, '--------selectedValue-----towerValue-', towerValue);
//
//        // Move these inside the function to ensure they are always retrieved when needed
//        const project_section_div = this.$('#project_section_div');
//        const tower_section_div = this.$('#tower_section_div');
//
//        if (!project_section_div || !tower_section_div) {
//            console.error("One or more sections are missing in the DOM");
//            return;
//        }
//
//        function showSection(section) {
//            project_section_div.addClass('d-none');
//            tower_section_div.addClass('d-none');
//            console.error("=========Section===============", section);
//            if (section === 'Select Tower') {
//                project_section_div.removeClass('d-none');
//            } else
////             if (section === 'complete')
//              {
//                tower_section_div.removeClass('d-none');
//            }
//        }
//        showSection(selectedValue);
//    },


    //    Pi Chart for Project Wise
    onchange_render_project_wise:function(){
        var self = this;
        var project_detailsValue = this.$('#project_details').val();
        console.log('=======project_detailsValue========', project_detailsValue)
        var selectedValue = this.$('#project_type').val();
        $('.project_graph').empty();
        var w = 200;
        var h = 200;
        var r = h/2;
        var elem = this.$('.project_graph');
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
            model: "project.info",
            method: "get_project_wise_details_new",
            args: [selectedValue, project_detailsValue],
        }).then(function (data) {
            var segColor = {};
            var vis = d3.select(elem[0]).append("svg:svg").data([data]).attr("width", w).attr("height", h).append("svg:g").attr("transform", "translate(" + r + "," + r + ")");
            var pie = d3.layout.pie().value(function(d){return d.value;});
            var arc = d3.svg.arc().outerRadius(r);
            var arcs = vis.selectAll("g.slice").data(pie).enter().append("svg:g").attr("class", "slice");
            arcs.append("svg:path")
                .attr("fill", function(d, i){
                    return color(i);
                })
                .attr("d", function (d) {
                    return arc(d);
                });

            var legend = d3.select(elem[0]).append("table").attr('class','legend');

            // create one row per segment.
            var tr = legend.append("tbody").selectAll("tr").data(data).enter().append("tr");

            // create the first column for each segment.
            tr.append("td").append("svg").attr("width", '20').attr("height", '30').append("rect")
                .attr("width", '30').attr("height", '25')
                .attr("fill",function(d, i){ return color(i) });

            // create the second column for each segment.
            tr.append("td").text(function(d){ return d.label;});

            // create the third column for each segment.
            tr.append("td").attr("class",'legendFreq')
                .text(function(d){ return d.value;});
        });
//        var selectedValue = this.$('#project_type').val();
//        var towerValue = this.$('#tower_type').val();
//        console.log(selectedValue, '--------selectedValue-----towerValue-', towerValue);
//        const project_section_div = this.$('#project_section_div');
//        const tower_section_div = this.$('#tower_section_div');
//        if (!project_section_div || !tower_section_div) {
//            console.error("One or more sections are missing in the DOM");
//            return;
//        }
//        function showSection(section) {
//            project_section_div.addClass('d-none');
//            tower_section_div.addClass('d-none');
//            console.error("=========Section===============", section);
//            if (section !== 'Select Tower') {
////                tower_section_div.removeClass('d-none');
//                project_section_div.removeClass('d-none');
//            } else
////             if (section === 'complete')
//              {
//                tower_section_div.removeClass('d-none');
//            }
//        }
//        showSection(selectedValue);
    },

    //    Pi Chart for Tower Wise
    onchange_render_tower_wise:function(){
        var self = this;
//        var selectedValue = $('#tower_type').on('change').val();
        var project_detailsValue = this.$('#project_details').val();
        var projectValue = this.$('#project_type').val();
        var selectedValue = this.$('#tower_type').val();
//        console.log(projectValue, 'projectValue============23456=======', selectedValue)
        $('.tower_graph').empty();
        var w = 200;
        var h = 200;
        var r = h/2;
        var elem = this.$('.tower_graph');
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
            model: "project.tower",
            method: "get_tower_wise_details",
            args: [selectedValue, projectValue, project_detailsValue],
        }).then(function (data) {
            var segColor = {};
            var vis = d3.select(elem[0]).append("svg:svg").data([data]).attr("width", w).attr("height", h).append("svg:g").attr("transform", "translate(" + r + "," + r + ")");
            var pie = d3.layout.pie().value(function(d){return d.value;});
            var arc = d3.svg.arc().outerRadius(r);
            var arcs = vis.selectAll("g.slice").data(pie).enter().append("svg:g").attr("class", "slice");
            arcs.append("svg:path")
                .attr("fill", function(d, i){
                    return color(i);
                })
                .attr("d", function (d) {
                    return arc(d);
                });

            var legend = d3.select(elem[0]).append("table").attr('class','legend');

            // create one row per segment.
            var tr = legend.append("tbody").selectAll("tr").data(data).enter().append("tr");

            // create the first column for each segment.
            tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                .attr("width", '16').attr("height", '16')
                .attr("fill",function(d, i){ return color(i) });

            // create the second column for each segment.
            tr.append("td").text(function(d){ return d.label;});

            // create the third column for each segment.
            tr.append("td").attr("class",'legendFreq')
                .text(function(d){ return d.value;});
        });
    },

    //    Pi Chart for Floor Wise
    onchange_render_floor_wise:function(){
        var self = this;
//        var selectedValue = $('#floor_type').on('change').val();
        var selectedValue = this.$('#floor_type').val();
        $('.floor_graph').empty();
        var w = 200;
        var h = 200;
        var r = h/2;
        var elem = this.$('.floor_graph');
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
            model: "project.floors",
            method: "get_floor_wise_details",
            args: [selectedValue], // Pass selectedValue as an argument
        }).then(function (data) {
            var segColor = {};
            var vis = d3.select(elem[0]).append("svg:svg").data([data]).attr("width", w).attr("height", h).append("svg:g").attr("transform", "translate(" + r + "," + r + ")");
            var pie = d3.layout.pie().value(function(d){return d.value;});
            var arc = d3.svg.arc().outerRadius(r);
            var arcs = vis.selectAll("g.slice").data(pie).enter().append("svg:g").attr("class", "slice");
            arcs.append("svg:path")
                .attr("fill", function(d, i){
                    return color(i);
                })
                .attr("d", function (d) {
                    return arc(d);
                });

            var legend = d3.select(elem[0]).append("table").attr('class','legend');

            // create one row per segment.
            var tr = legend.append("tbody").selectAll("tr").data(data).enter().append("tr");

            // create the first column for each segment.
            tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                .attr("width", '16').attr("height", '16')
                .attr("fill",function(d, i){ return color(i) });

            // create the second column for each segment.
            tr.append("td").text(function(d){ return d.label;});

            // create the third column for each segment.
            tr.append("td").attr("class",'legendFreq')
                .text(function(d){ return d.value;});
        });
    },

    //    Pi Chart for Flat Wise
    onchange_render_flat_wise:function(){
        var self = this;
//        var selectedValue = $('#flat_type').on('change').val();
        var selectedValue = this.$('#flat_type').val();
        $('.flat_graph').empty();
        var w = 200;
        var h = 200;
        var r = h/2;
        var elem = this.$('.flat_graph');
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
            model: "project.flats",
            method: "get_flat_wise_details",
            args: [selectedValue], // Pass selectedValue as an argument
        }).then(function (data) {
            var segColor = {};
            var vis = d3.select(elem[0]).append("svg:svg").data([data]).attr("width", w).attr("height", h).append("svg:g").attr("transform", "translate(" + r + "," + r + ")");
            var pie = d3.layout.pie().value(function(d){return d.value;});
            var arc = d3.svg.arc().outerRadius(r);
            var arcs = vis.selectAll("g.slice").data(pie).enter().append("svg:g").attr("class", "slice");
            arcs.append("svg:path")
                .attr("fill", function(d, i){
                    return color(i);
                })
                .attr("d", function (d) {
                    return arc(d);
                });

            var legend = d3.select(elem[0]).append("table").attr('class','legend');

            // create one row per segment.
            var tr = legend.append("tbody").selectAll("tr").data(data).enter().append("tr");

            // create the first column for each segment.
            tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                .attr("width", '16').attr("height", '16')
                .attr("fill",function(d, i){ return color(i) });

            // create the second column for each segment.
            tr.append("td").text(function(d){ return d.label;});

            // create the third column for each segment.
            tr.append("td").attr("class",'legendFreq')
                .text(function(d){ return d.value;});
        });
    },

   //   Render ALL given below  Bar graph
//    render_graphs: function(){
//        var self = this;
//        self.render_bar_chart();
//    },
//    render_pending_graphs_c_m_a: function(){
//        var self = this;
//        self.render_pending_bar_chart_c_m_a();
//    },
//    render_graphs_tower: function(){
//        var self = this;
//        self.render_bar_chart_tower();
//    },
    render_graphs_floor: function(){
        var self = this;
        self.render_bar_chart_floor();
    },
    render_graphs_flat: function(){
        var self = this;
        self.render_bar_chart_flat();
    },

   // Bar Chart of complete checker maker Approver
//    render_bar_chart_c_m_a: function() {
//        var self = this;
//        var projectValue = this.$('#project_type').val();
//        var towerValue = this.$('#tower_type').val();
//        console.log(projectValue, 'projectValue==========towerValue=====', towerValue);
//        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433', '#ffc25b', '#f8e54b'];
//        var color = d3.scale.ordinal().range(colors);
//
//        rpc.query({
//            model: "project.info",
//            method: "get_c_m_a_data",
//            args: [projectValue, towerValue],
//        }).then(function(data) {
//            var fData = data[0];
//            var dept = data[1];
//            var id = self.$('.c_m_a_graph')[0];
//            var barColor = '#ff618a';
//
//            fData.forEach(function(d) {
//                var total = 0;
//                for (var dpt in dept) {
//                    total += d.leave[dept[dpt]];
//                }
//                d.total = total;
//            });
//
//            function histoGram(fD) {
//                var hG = {}, hGDim = {t: 60, r: 0, b: 30, l: 0};
//                hGDim.w = 350 - hGDim.l - hGDim.r,
//                hGDim.h = 200 - hGDim.t - hGDim.b;
//
//                var hGsvg = d3.select(id).append("svg")
//                    .attr("width", hGDim.w + hGDim.l + hGDim.r)
//                    .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
//                    .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");
//
//                var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
//                    .domain(fD.map(function(d) { return d[0]; }));
//
//                hGsvg.append("g").attr("class", "x axis")
//                    .attr("transform", "translate(0," + hGDim.h + ")")
//                    .call(d3.svg.axis().scale(x).orient("bottom"));
//
//                var y = d3.scale.linear().range([hGDim.h, 0])
//                    .domain([0, d3.max(fD, function(d) { return d[1]; })]);
//
//                var bars = hGsvg.selectAll(".bar").data(fD).enter()
//                    .append("g").attr("class", "bar");
//
//                bars.append("rect")
//                    .attr("x", function(d) { return x(d[0]); })
//                    .attr("y", function(d) { return y(d[1]); })
//                    .attr("width", x.rangeBand())
//                    .attr("height", function(d) { return hGDim.h - y(d[1]); })
//                    .attr('fill', barColor)
//                    .on("mouseover", mouseover)
//                    .on("mouseout", mouseout);
//
//                bars.append("text").text(function(d) { return d3.format(",")(d[1]) })
//                    .attr("x", function(d) { return x(d[0]) + x.rangeBand() / 2; })
//                    .attr("y", function(d) { return y(d[1]) - 5; })
//                    .attr("text-anchor", "middle");
//
//                function mouseover(d) {
//                    var st = fData.filter(function(s) { return s.l_month == d[0]; })[0],
//                        nD = d3.keys(st.leave).map(function(s) { return { type: s, leave: st.leave[s] }; });
//                    leg.update(nD);
//                }
//
//                function mouseout(d) {
//                    leg.update(tF);
//                }
//
//                hG.update = function(nD, color) {
//                    y.domain([0, d3.max(nD, function(d) { return d[1]; })]);
//                    var bars = hGsvg.selectAll(".bar").data(nD);
//                    bars.select("rect").transition().duration(500)
//                        .attr("y", function(d) { return y(d[1]); })
//                        .attr("height", function(d) { return hGDim.h - y(d[1]); })
//                        .attr("fill", color);
//                    bars.select("text").transition().duration(500)
//                        .text(function(d) { return d3.format(",")(d[1]) })
//                        .attr("y", function(d) { return y(d[1]) - 5; });
//                }
//                return hG;
//            }
//
//            function legend(lD) {
//                var leg = {};
//                var legend = d3.select(id).append("table").attr('class', 'legend');
//                var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");
//                tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
//                    .attr("width", '16').attr("height", '16')
//                    .attr("fill", function(d, i) { return color(i); })
//                tr.append("td").text(function(d) { return d.type; });
//                tr.append("td").attr("class", 'legendFreq')
//                    .text(function(d) { return d.l_month; });
//                tr.append("td").attr("class", 'legendPerc')
//                    .text(function(d) { return getLegend(d, lD); });
//                leg.update = function(nD) {
//                    var l = legend.select("tbody").selectAll("tr").data(nD);
//                    l.select(".legendFreq").text(function(d) { return d3.format(",")(d.leave); });
//                    l.select(".legendPerc").text(function(d) { return getLegend(d, nD); });
//                }
//                function getLegend(d, aD) {
//                    var perc = (d.leave / d3.sum(aD.map(function(v) { return v.leave; })));
//                    if (isNaN(perc)) {
//                        return d3.format("%")(0);
//                    } else {
//                        return d3.format("%")(d.leave / d3.sum(aD.map(function(v) { return v.leave; })));
//                    }
//                }
//                return leg;
//            }
//
//            var tF = dept.map(function(d) {
//                return { type: d, leave: d3.sum(fData.map(function(t) { return t.leave[d]; })) };
//            });
//
//            var sF = fData.map(function(d) { return [d.l_month, d.total]; });
//
//            var hG = histoGram(sF),
//                leg = legend(tF);
//        });
//    },

    // Bar Chart of complete checker maker Approver
    render_bar_chart_c_m_a: function() {
    var self = this;
    var project_detailsValue = this.$('#project_details').val();
    var projectValue = this.$('#project_type').val();
    var towerValue = this.$('#tower_type').val();
    console.log(projectValue, 'projectValue==========towerValue=====', towerValue);
    var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433', '#ffc25b', '#f8e54b'];
    var color = d3.scale.ordinal().range(colors);

    rpc.query({
        model: "project.info",
        method: "get_c_m_a_data",
        args: [projectValue, towerValue, project_detailsValue],
    }).then(function(data) {
        var fData = data[0];
        var dept = data[1];
        var id = self.$('.c_m_a_graph')[0];
        var barColor = '#ff618a';

        // Clear previous chart
        d3.select(id).selectAll("*").remove();

        fData.forEach(function(d) {
            var total = 0;
            for (var dpt in dept) {
                total += d.leave[dept[dpt]];
            }
            d.total = total;
        });

        function histoGram(fD) {
            var hG = {}, hGDim = {t: 60, r: 0, b: 30, l: 0};
            hGDim.w = 350 - hGDim.l - hGDim.r,
            hGDim.h = 200 - hGDim.t - hGDim.b;

            var hGsvg = d3.select(id).append("svg")
                .attr("width", hGDim.w + hGDim.l + hGDim.r)
                .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
                .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");

            var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
                .domain(fD.map(function(d) { return d[0]; }));

            hGsvg.append("g").attr("class", "x axis")
                .attr("transform", "translate(0," + hGDim.h + ")")
                .call(d3.svg.axis().scale(x).orient("bottom"));

            var y = d3.scale.linear().range([hGDim.h, 0])
                .domain([0, d3.max(fD, function(d) { return d[1]; })]);

            var bars = hGsvg.selectAll(".bar").data(fD).enter()
                .append("g").attr("class", "bar");

            bars.append("rect")
                .attr("x", function(d) { return x(d[0]); })
                .attr("y", function(d) { return y(d[1]); })
                .attr("width", x.rangeBand())
                .attr("height", function(d) { return hGDim.h - y(d[1]); })
                .attr('fill', barColor)
                .on("mouseover", mouseover)
                .on("mouseout", mouseout);

            bars.append("text").text(function(d) { return d3.format(",")(d[1]) })
                .attr("x", function(d) { return x(d[0]) + x.rangeBand() / 2; })
                .attr("y", function(d) { return y(d[1]) - 5; })
                .attr("text-anchor", "middle");

            function mouseover(d) {
                var st = fData.filter(function(s) { return s.l_month == d[0]; })[0],
                    nD = d3.keys(st.leave).map(function(s) { return { type: s, leave: st.leave[s] }; });
                leg.update(nD);
            }

            function mouseout(d) {
                leg.update(tF);
            }

            hG.update = function(nD, color) {
                y.domain([0, d3.max(nD, function(d) { return d[1]; })]);
                var bars = hGsvg.selectAll(".bar").data(nD);
                bars.select("rect").transition().duration(500)
                    .attr("y", function(d) { return y(d[1]); })
                    .attr("height", function(d) { return hGDim.h - y(d[1]); })
                    .attr("fill", color);
                bars.select("text").transition().duration(500)
                    .text(function(d) { return d3.format(",")(d[1]) })
                    .attr("y", function(d) { return y(d[1]) - 5; });
            }
            return hG;
        }

        function legend(lD) {
            var leg = {};
            var legend = d3.select(id).append("table").attr('class', 'legend');
            var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");
            tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                .attr("width", '16').attr("height", '16')
                .attr("fill", function(d, i) { return color(i); })
            tr.append("td").text(function(d) { return d.type; });
            tr.append("td").attr("class", 'legendFreq')
                .text(function(d) { return d.l_month; });
            tr.append("td").attr("class", 'legendPerc')
                .text(function(d) { return getLegend(d, lD); });
            leg.update = function(nD) {
                var l = legend.select("tbody").selectAll("tr").data(nD);
                l.select(".legendFreq").text(function(d) { return d3.format(",")(d.leave); });
                l.select(".legendPerc").text(function(d) { return getLegend(d, nD); });
            }
            function getLegend(d, aD) {
                var perc = (d.leave / d3.sum(aD.map(function(v) { return v.leave; })));
                if (isNaN(perc)) {
                    return d3.format("%")(0);
                } else {
                    return d3.format("%")(d.leave / d3.sum(aD.map(function(v) { return v.leave; })));
                }
            }
            return leg;
        }

        var tF = dept.map(function(d) {
            return { type: d, leave: d3.sum(fData.map(function(t) { return t.leave[d]; })) };
        });

        var sF = fData.map(function(d) { return [d.l_month, d.total]; });

        var hG = histoGram(sF),
            leg = legend(tF);
    });
    },

    // Bar Chart for pending checker maker Approver
//    render_pending_bar_chart_c_m_a:function(){
//        var self = this;
//        var projectValue = this.$('#project_type').val();
//        var towerValue = this.$('#tower_type').val();
//        console.log(projectValue, 'projectValue==========towerValue=====', towerValue);
//        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1',
//         '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
//        '#ffa433', '#ffc25b', '#f8e54b'];
//        var color = d3.scale.ordinal().range(colors);
//        rpc.query({
//                model: "project.info",
//                method: "get_pending_c_m_a_data",
//                args:[projectValue,towerValue]
//            }).then(function (data) {
//                var fData = data[0];
//                var dept = data[1];
//                var id = self.$('.pending_c_m_a_graph')[0];
//                var barColor = '#ff618a';
//                // compute total for each state.
//                fData.forEach(function(d){
//                    var total = 0;
//                    for (var dpt in dept){
//                        total += d.leave[dept[dpt]];
//                    }
//                d.total=total;
//                });
//
//                // function to handle histogram.
//                function histoGram(fD){
//                    var hG={},    hGDim = {t: 60, r: 0, b: 30, l: 0};
//                    hGDim.w = 350 - hGDim.l - hGDim.r,
//                    hGDim.h = 200 - hGDim.t - hGDim.b;
//
//                    //create svg for histogram.
//                    var hGsvg = d3.select(id).append("svg")
//                        .attr("width", hGDim.w + hGDim.l + hGDim.r)
//                        .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
//                        .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");
//
//                    // create function for x-axis mapping.
//                    var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
//                            .domain(fD.map(function(d) { return d[0]; }));
//
//                    // Add x-axis to the histogram svg.
//                    hGsvg.append("g").attr("class", "x axis")
//                        .attr("transform", "translate(0," + hGDim.h + ")")
//                        .call(d3.svg.axis().scale(x).orient("bottom"));
//
//                    // Create function for y-axis map.
//                    var y = d3.scale.linear().range([hGDim.h, 0])
//                            .domain([0, d3.max(fD, function(d) { return d[1]; })]);
//
//                    // Create bars for histogram to contain rectangles and freq labels.
//                    var bars = hGsvg.selectAll(".bar").data(fD).enter()
//                            .append("g").attr("class", "bar");
//
//                    //create the rectangles.
//                    bars.append("rect")
//                        .attr("x", function(d) { return x(d[0]); })
//                        .attr("y", function(d) { return y(d[1]); })
//                        .attr("width", x.rangeBand())
//                        .attr("height", function(d) { return hGDim.h - y(d[1]); })
//                        .attr('fill',barColor)
//                        .on("mouseover",mouseover)// mouseover is defined below.
//                        .on("mouseout",mouseout);// mouseout is defined below.
//
//                    //Create the frequency labels above the rectangles.
//                    bars.append("text").text(function(d){ return d3.format(",")(d[1])})
//                        .attr("x", function(d) { return x(d[0])+x.rangeBand()/2; })
//                        .attr("y", function(d) { return y(d[1])-5; })
//                        .attr("text-anchor", "middle");
//
//                    function mouseover(d){  // utility function to be called on mouseover.
//                        // filter for selected state.
//                        var st = fData.filter(function(s){ return s.l_month == d[0];})[0],
//                            nD = d3.keys(st.leave).map(function(s){ return {type:s, leave:st.leave[s]};});
//
//                        // call update functions of pie-chart and legend.
////                        pC.update(nD);
//                        leg.update(nD);
//                    }
//
//                    function mouseout(d){    // utility function to be called on mouseout.
//                        // reset the pie-chart and legend.
////                        pC.update(tF);
//                        leg.update(tF);
//                    }
//
//                    // create function to update the bars. This will be used by pie-chart.
//                    hG.update = function(nD, color){
//                        // update the domain of the y-axis map to reflect change in frequencies.
//                        y.domain([0, d3.max(nD, function(d) { return d[1]; })]);
//
//                        // Attach the new data to the bars.
//                        var bars = hGsvg.selectAll(".bar").data(nD);
//
//                        // transition the height and color of rectangles.
//                        bars.select("rect").transition().duration(500)
//                            .attr("y", function(d) {return y(d[1]); })
//                            .attr("height", function(d) { return hGDim.h - y(d[1]); })
//                            .attr("fill", color);
//
//                        // transition the frequency labels location and change value.
//                        bars.select("text").transition().duration(500)
//                            .text(function(d){ return d3.format(",")(d[1])})
//                            .attr("y", function(d) {return y(d[1])-5; });
//                    }
//                    return hG;
//                }
//                // function to handle legend.
//                function legend(lD){
//                    var leg = {};
//
//                    // create table for legend.
//                    var legend = d3.select(id).append("table").attr('class','legend');
//
//                    // create one row per segment.
//                    var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");
//
//                    // create the first column for each segment.
//                    tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
//                        .attr("width", '16').attr("height", '16')
//                        .attr("fill", function(d, i){return color(i);})
//
//                    // create the second column for each segment.
//                    tr.append("td").text(function(d){ return d.type;});
//
//                    // create the third column for each segment.
//                    tr.append("td").attr("class",'legendFreq')
//                        .text(function(d){ return d.l_month;});
//
//                    // create the fourth column for each segment.
//                    tr.append("td").attr("class",'legendPerc')
//                        .text(function(d){ return getLegend(d,lD);});
//
//                    // Utility function to be used to update the legend.
//                    leg.update = function(nD){
//                        // update the data attached to the row elements.
//                        var l = legend.select("tbody").selectAll("tr").data(nD);
//
//                        // update the frequencies.
//                        l.select(".legendFreq").text(function(d){ return d3.format(",")(d.leave);});
//
//                        // update the percentage column.
//                        l.select(".legendPerc").text(function(d){ return getLegend(d,nD);});
//                    }
//
//                    function getLegend(d,aD){ // Utility function to compute percentage.
//                        var perc = (d.leave/d3.sum(aD.map(function(v){ return v.leave; })));
//                        if (isNaN(perc)){
//                            return d3.format("%")(0);
//                            }
//                        else{
//                            return d3.format("%")(d.leave/d3.sum(aD.map(function(v){ return v.leave; })));
//                            }
//                    }
//
//                    return leg;
//                }
//
//                // calculate total frequency by segment for all state.
//                var tF = dept.map(function(d){
//                    return {type:d, leave: d3.sum(fData.map(function(t){ return t.leave[d];}))};
//                });
//
//                // calculate total frequency by state for all segment.
//                var sF = fData.map(function(d){return [d.l_month,d.total];});
//
//                var hG = histoGram(sF), // create the histogram.
//                    leg= legend(tF);  // create the legend.
//        });
//    },


    // Bar Chart for pending checker maker Approver
    render_pending_bar_chart_c_m_a: function() {
        var self = this;
        var projectValue = this.$('#project_type').val();
        var towerValue = this.$('#tower_type').val();
        console.log(projectValue, 'projectValue==========towerValue=====', towerValue);
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1',
            '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
            '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);

        rpc.query({
            model: "project.info",
            method: "get_pending_c_m_a_data",
            args: [projectValue, towerValue]
        }).then(function(data) {
            var fData = data[0];
            var dept = data[1];
            var id = self.$('.pending_c_m_a_graph')[0];
            var barColor = '#ff618a';

            // Clear previous chart
            d3.select(id).selectAll("*").remove();

            // Compute total for each state
            fData.forEach(function(d) {
                var total = 0;
                for (var dpt in dept) {
                    total += d.leave[dept[dpt]];
                }
                d.total = total;
            });

            // Function to handle histogram
            function histoGram(fD) {
                var hG = {}, hGDim = { t: 60, r: 0, b: 30, l: 0 };
                hGDim.w = 350 - hGDim.l - hGDim.r,
                    hGDim.h = 200 - hGDim.t - hGDim.b;

                // Create svg for histogram
                var hGsvg = d3.select(id).append("svg")
                    .attr("width", hGDim.w + hGDim.l + hGDim.r)
                    .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
                    .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");

                // Create function for x-axis mapping
                var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
                    .domain(fD.map(function(d) { return d[0]; }));

                // Add x-axis to the histogram svg
                hGsvg.append("g").attr("class", "x axis")
                    .attr("transform", "translate(0," + hGDim.h + ")")
                    .call(d3.svg.axis().scale(x).orient("bottom"));

                // Create function for y-axis map
                var y = d3.scale.linear().range([hGDim.h, 0])
                    .domain([0, d3.max(fD, function(d) { return d[1]; })]);

                // Create bars for histogram to contain rectangles and freq labels
                var bars = hGsvg.selectAll(".bar").data(fD).enter()
                    .append("g").attr("class", "bar");

                // Create the rectangles
                bars.append("rect")
                    .attr("x", function(d) { return x(d[0]); })
                    .attr("y", function(d) { return y(d[1]); })
                    .attr("width", x.rangeBand())
                    .attr("height", function(d) { return hGDim.h - y(d[1]); })
                    .attr('fill', barColor)
                    .on("mouseover", mouseover) // mouseover is defined below
                    .on("mouseout", mouseout);  // mouseout is defined below

                // Create the frequency labels above the rectangles
                bars.append("text").text(function(d) { return d3.format(",")(d[1]) })
                    .attr("x", function(d) { return x(d[0]) + x.rangeBand() / 2; })
                    .attr("y", function(d) { return y(d[1]) - 5; })
                    .attr("text-anchor", "middle");

                function mouseover(d) { // utility function to be called on mouseover
                    // filter for selected state
                    var st = fData.filter(function(s) { return s.l_month == d[0]; })[0],
                        nD = d3.keys(st.leave).map(function(s) { return { type: s, leave: st.leave[s] }; });

                    // call update functions of pie-chart and legend
                    leg.update(nD);
                }

                function mouseout(d) { // utility function to be called on mouseout
                    // reset the pie-chart and legend
                    leg.update(tF);
                }

                // Create function to update the bars. This will be used by pie-chart
                hG.update = function(nD, color) {
                    // update the domain of the y-axis map to reflect change in frequencies
                    y.domain([0, d3.max(nD, function(d) { return d[1]; })]);

                    // Attach the new data to the bars
                    var bars = hGsvg.selectAll(".bar").data(nD);

                    // transition the height and color of rectangles
                    bars.select("rect").transition().duration(500)
                        .attr("y", function(d) { return y(d[1]); })
                        .attr("height", function(d) { return hGDim.h - y(d[1]); })
                        .attr("fill", color);

                    // transition the frequency labels location and change value
                    bars.select("text").transition().duration(500)
                        .text(function(d) { return d3.format(",")(d[1]) })
                        .attr("y", function(d) { return y(d[1]) - 5; });
                }
                return hG;
            }

            // Function to handle legend
            function legend(lD) {
                var leg = {};

                // Create table for legend
                var legend = d3.select(id).append("table").attr('class', 'legend');

                // Create one row per segment
                var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");

                // Create the first column for each segment
                tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                    .attr("width", '16').attr("height", '16')
                    .attr("fill", function(d, i) { return color(i); })

                // Create the second column for each segment
                tr.append("td").text(function(d) { return d.type; });

                // Create the third column for each segment
                tr.append("td").attr("class", 'legendFreq')
                    .text(function(d) { return d.l_month; });

                // Create the fourth column for each segment
                tr.append("td").attr("class", 'legendPerc')
                    .text(function(d) { return getLegend(d, lD); });

                // Utility function to be used to update the legend
                leg.update = function(nD) {
                    // update the data attached to the row elements
                    var l = legend.select("tbody").selectAll("tr").data(nD);

                    // update the frequencies
                    l.select(".legendFreq").text(function(d) { return d3.format(",")(d.leave); });

                    // update the percentage column
                    l.select(".legendPerc").text(function(d) { return getLegend(d, nD); });
                }

                function getLegend(d, aD) { // Utility function to compute percentage
                    var perc = (d.leave / d3.sum(aD.map(function(v) { return v.leave; })));
                    if (isNaN(perc)) {
                        return d3.format("%")(0);
                    } else {
                        return d3.format("%")(d.leave / d3.sum(aD.map(function(v) { return v.leave; })));
                    }
                }

                return leg;
            }

            // Calculate total frequency by segment for all state
            var tF = dept.map(function(d) {
                return { type: d, leave: d3.sum(fData.map(function(t) { return t.leave[d]; })) };
            });

            // Calculate total frequency by state for all segment
            var sF = fData.map(function(d) { return [d.l_month, d.total]; });

            var hG = histoGram(sF), // create the histogram
                leg = legend(tF);  // create the legend
        });
    },

    // Bar Chart NC YC GC OR & RC Project
    render_bar_chart: function() {
        var self = this;
        var projectValue = this.$('#project_type').val();
        var towerValue = this.$('#tower_type').val();
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);

        // Remove existing chart elements before rendering new ones
        self.$('.project_graph_count').empty();

        rpc.query({
            model: "project.info",
            method: "get_project_nc_count",
            args: [projectValue, towerValue]
        }).then(function(data) {
            var fData = data[0];
            var dept = data[1];
            var id = self.$('.project_graph_count')[0];
            var barColor = '#ff618a';

            // compute total for each state.
            fData.forEach(function(d) {
                var total = 0;
                for (var dpt in dept) {
                    total += d.leave[dept[dpt]];
                }
                d.total = total;
            });

            // function to handle histogram.
            function histoGram(fD) {
                var hG = {},
                    hGDim = { t: 60, r: 0, b: 30, l: 0 };
                hGDim.w = 350 - hGDim.l - hGDim.r,
                hGDim.h = 200 - hGDim.t - hGDim.b;

                // create svg for histogram.
                var hGsvg = d3.select(id).append("svg")
                    .attr("width", hGDim.w + hGDim.l + hGDim.r)
                    .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
                    .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");

                // create function for x-axis mapping.
                var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
                    .domain(fD.map(function(d) { return d[0]; }));

                // Add x-axis to the histogram svg.
                hGsvg.append("g").attr("class", "x axis")
                    .attr("transform", "translate(0," + hGDim.h + ")")
                    .call(d3.svg.axis().scale(x).orient("bottom"));

                // Create function for y-axis map.
                var y = d3.scale.linear().range([hGDim.h, 0])
                    .domain([0, d3.max(fD, function(d) { return d[1]; })]);

                // Create bars for histogram to contain rectangles and freq labels.
                var bars = hGsvg.selectAll(".bar").data(fD).enter()
                    .append("g").attr("class", "bar");

                // create the rectangles.
                bars.append("rect")
                    .attr("x", function(d) { return x(d[0]); })
                    .attr("y", function(d) { return y(d[1]); })
                    .attr("width", x.rangeBand())
                    .attr("height", function(d) { return hGDim.h - y(d[1]); })
                    .attr('fill', barColor)
                    .on("mouseover", mouseover) // mouseover is defined below.
                    .on("mouseout", mouseout); // mouseout is defined below.

                // Create the frequency labels above the rectangles.
                bars.append("text").text(function(d) { return d3.format(",")(d[1]) })
                    .attr("x", function(d) { return x(d[0]) + x.rangeBand() / 2; })
                    .attr("y", function(d) { return y(d[1]) - 5; })
                    .attr("text-anchor", "middle");

                function mouseover(d) { // utility function to be called on mouseover.
                    // filter for selected state.
                    var st = fData.filter(function(s) { return s.l_month == d[0]; })[0],
                        nD = d3.keys(st.leave).map(function(s) { return { type: s, leave: st.leave[s] }; });

                    // call update functions of legend.
                    leg.update(nD);
                }

                function mouseout(d) { // utility function to be called on mouseout.
                    // reset the legend.
                    leg.update(tF);
                }

                // create function to update the bars. This will be used by pie-chart.
                hG.update = function(nD, color) {
                    // update the domain of the y-axis map to reflect change in frequencies.
                    y.domain([0, d3.max(nD, function(d) { return d[1]; })]);

                    // Attach the new data to the bars.
                    var bars = hGsvg.selectAll(".bar").data(nD);

                    // transition the height and color of rectangles.
                    bars.select("rect").transition().duration(500)
                        .attr("y", function(d) { return y(d[1]); })
                        .attr("height", function(d) { return hGDim.h - y(d[1]); })
                        .attr("fill", color);

                    // transition the frequency labels location and change value.
                    bars.select("text").transition().duration(500)
                        .text(function(d) { return d3.format(",")(d[1]) })
                        .attr("y", function(d) { return y(d[1]) - 5; });
                }
                return hG;
            }

            // function to handle legend.
            function legend(lD) {
                var leg = {};

                // create div for legend and add a scrollable container.
                var legendDiv = d3.select(id).append("div").attr('class', 'legend-container')
                    .style('overflow-y', 'auto')
                    .style('max-height', '200px'); // adjust max-height as needed

                // create table for legend.
                var legend = legendDiv.append("table").attr('class', 'legend');

                // create one row per segment.
                var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");

                // create the first column for each segment.
                tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                    .attr("width", '16').attr("height", '16')
                    .attr("fill", function(d, i) { return color(i); });

                // create the second column for each segment.
                tr.append("td").text(function(d) { return d.type; });

                // create the third column for each segment.
                tr.append("td").attr("class", 'legendFreq')
                    .text(function(d) { return d3.format(",")(d.leave); });

                // create the fourth column for each segment.
                tr.append("td").attr("class", 'legendPerc')
                    .text(function(d) { return getLegend(d, lD); });

                // Utility function to be used to update the legend.
                leg.update = function(nD) {
                    // update the data attached to the row elements.
                    var l = legend.select("tbody").selectAll("tr").data(nD);

                    // update the frequencies.
                    l.select(".legendFreq").text(function(d) { return d3.format(",")(d.leave); });

                    // update the percentage column.
                    l.select(".legendPerc").text(function(d) { return getLegend(d, nD); });
                }

                function getLegend(d, aD) { // Utility function to compute percentage.
                    var perc = (d.leave / d3.sum(aD.map(function(v) { return v.leave; })));
                    if (isNaN(perc)) {
                        return d3.format("%")(0);
                    } else {
                        return d3.format("%")(d.leave / d3.sum(aD.map(function(v) { return v.leave; })));
                    }
                }

                return leg;
            }

            // calculate total frequency by segment for all state.
            var tF = dept.map(function(d) {
                return { type: d, leave: d3.sum(fData.map(function(t) { return t.leave[d]; })) };
            });

            // calculate total frequency by state for all segment.
            var sF = fData.map(function(d) { return [d.l_month, d.total]; });
            var hG = histoGram(sF), // create the histogram.
                leg = legend(tF); // create the legend.
        });
    },

    // Bar Chart NC YC GC OR & RC for Tower
    render_bar_chart_tower: function(){
        var self = this;
        var projectValue = this.$('#project_type').val();
        var towerValue = this.$('#tower_type').val();
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1',
                      '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
                      '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        // Clear any existing chart and legend elements before rendering new ones.
        d3.select(this.$('.tower_graph_count')[0]).selectAll('*').remove();

        rpc.query({
            model: "project.tower",
            method: "get_tower_counts",
            args: [projectValue, towerValue]
        }).then(function (data) {
            var fData = data[0];
            var dept = data[1];
            var id = self.$('.tower_graph_count')[0];
            var barColor = '#ff618a';

            // Compute total for each state.
            fData.forEach(function(d){
                var total = 0;
                for (var dpt in dept){
                    total += d.leave[dept[dpt]];
                }
                d.total = total;
            });

            // Function to handle histogram.
            function histoGram(fD){
                var hG = {}, hGDim = {t: 60, r: 0, b: 30, l: 0};
                hGDim.w = 350 - hGDim.l - hGDim.r;
                hGDim.h = 200 - hGDim.t - hGDim.b;

                // Create SVG for histogram.
                var hGsvg = d3.select(id).append("svg")
                    .attr("width", hGDim.w + hGDim.l + hGDim.r)
                    .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
                    .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");

                // Create function for x-axis mapping.
                var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
                    .domain(fD.map(function(d) { return d[0]; }));

                // Add x-axis to the histogram SVG.
                hGsvg.append("g").attr("class", "x axis")
                    .attr("transform", "translate(0," + hGDim.h + ")")
                    .call(d3.svg.axis().scale(x).orient("bottom"));

                // Create function for y-axis map.
                var y = d3.scale.linear().range([hGDim.h, 0])
                    .domain([0, d3.max(fD, function(d) { return d[1]; })]);

                // Create bars for histogram to contain rectangles and freq labels.
                var bars = hGsvg.selectAll(".bar").data(fD).enter()
                    .append("g").attr("class", "bar");

                // Create the rectangles.
                bars.append("rect")
                    .attr("x", function(d) { return x(d[0]); })
                    .attr("y", function(d) { return y(d[1]); })
                    .attr("width", x.rangeBand())
                    .attr("height", function(d) { return hGDim.h - y(d[1]); })
                    .attr('fill', barColor)
                    .on("mouseover", mouseover)
                    .on("mouseout", mouseout);

                // Create the frequency labels above the rectangles.
                bars.append("text").text(function(d){ return d3.format(",")(d[1])})
                    .attr("x", function(d) { return x(d[0]) + x.rangeBand()/2; })
                    .attr("y", function(d) { return y(d[1]) - 5; })
                    .attr("text-anchor", "middle");

                function mouseover(d){
                    var st = fData.filter(function(s){ return s.l_month == d[0]; })[0],
                        nD = d3.keys(st.leave).map(function(s){ return {type: s, leave: st.leave[s]}; });
                    leg.update(nD);
                }

                function mouseout(d){
                    leg.update(tF);
                }

                // Create function to update the bars.
                hG.update = function(nD, color){
                    y.domain([0, d3.max(nD, function(d) { return d[1]; })]);

                    var bars = hGsvg.selectAll(".bar").data(nD);

                    bars.select("rect").transition().duration(500)
                        .attr("y", function(d) { return y(d[1]); })
                        .attr("height", function(d) { return hGDim.h - y(d[1]); })
                        .attr("fill", color);

                    bars.select("text").transition().duration(500)
                        .text(function(d){ return d3.format(",")(d[1]); })
                        .attr("y", function(d) { return y(d[1]) - 5; });
                }
                return hG;
            }

            // Function to handle legend.
            function legend(lD){
                var leg = {};

                var legendDiv = d3.select(id).append("div").attr('class', 'legend-container')
                    .style('overflow-y', 'auto')
                    .style('max-height', '200px');

                var legend = legendDiv.append("table").attr('class', 'legend');

                var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");

                tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                    .attr("width", '16').attr("height", '16')
                    .attr("fill", function(d, i){ return color(i); });

                tr.append("td").text(function(d){ return d.type; });

                tr.append("td").attr("class", 'legendFreq')
                    .text(function(d){ return d.l_month; });

                tr.append("td").attr("class", 'legendPerc')
                    .text(function(d){ return getLegend(d, lD); });

                leg.update = function(nD){
                    var l = legend.select("tbody").selectAll("tr").data(nD);

                    l.select(".legendFreq").text(function(d){ return d3.format(",")(d.leave); });

                    l.select(".legendPerc").text(function(d){ return getLegend(d, nD); });
                }

                function getLegend(d, aD){
                    var perc = d.leave / d3.sum(aD.map(function(v){ return v.leave; }));
                    if (isNaN(perc)){
                        return d3.format("%")(0);
                    } else {
                        return d3.format("%")(d.leave / d3.sum(aD.map(function(v){ return v.leave; })));
                    }
                }

                return leg;
            }

            var tF = dept.map(function(d){
                return { type: d, leave: d3.sum(fData.map(function(t){ return t.leave[d]; })) };
            });

            var sF = fData.map(function(d){ return [d.l_month, d.total]; });

            var hG = histoGram(sF), // Create the histogram.
                leg = legend(tF);  // Create the legend.
        });
    },

    // Bar Chart NC YC GC OR & RC for Flat
    render_bar_chart_flat:function(){
        var self = this;
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1',
         '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
                model: "project.flats",
                method: "get_flat_counts",
            }).then(function (data) {
                var fData = data[0];
                var dept = data[1];
                var id = self.$('.flat_graph_count')[0];
                var barColor = '#ff618a';
                // compute total for each state.
                fData.forEach(function(d){
                    var total = 0;
                    for (var dpt in dept){
                        total += d.leave[dept[dpt]];
                    }
                d.total=total;
                });

                // function to handle histogram.
                function histoGram(fD){
                    var hG={},    hGDim = {t: 60, r: 0, b: 30, l: 0};
                    hGDim.w = 350 - hGDim.l - hGDim.r,
                    hGDim.h = 200 - hGDim.t - hGDim.b;

                    //create svg for histogram.
                    var hGsvg = d3.select(id).append("svg")
                        .attr("width", hGDim.w + hGDim.l + hGDim.r)
                        .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
                        .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");

                    // create function for x-axis mapping.
                    var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
                            .domain(fD.map(function(d) { return d[0]; }));

                    // Add x-axis to the histogram svg.
                    hGsvg.append("g").attr("class", "x axis")
                        .attr("transform", "translate(0," + hGDim.h + ")")
                        .call(d3.svg.axis().scale(x).orient("bottom"));

                    // Create function for y-axis map.
                    var y = d3.scale.linear().range([hGDim.h, 0])
                            .domain([0, d3.max(fD, function(d) { return d[1]; })]);

                    // Create bars for histogram to contain rectangles and freq labels.
                    var bars = hGsvg.selectAll(".bar").data(fD).enter()
                            .append("g").attr("class", "bar");

                    //create the rectangles.
                    bars.append("rect")
                        .attr("x", function(d) { return x(d[0]); })
                        .attr("y", function(d) { return y(d[1]); })
                        .attr("width", x.rangeBand())
                        .attr("height", function(d) { return hGDim.h - y(d[1]); })
                        .attr('fill',barColor)
                        .on("mouseover",mouseover)// mouseover is defined below.
                        .on("mouseout",mouseout);// mouseout is defined below.

                    //Create the frequency labels above the rectangles.
                    bars.append("text").text(function(d){ return d3.format(",")(d[1])})
                        .attr("x", function(d) { return x(d[0])+x.rangeBand()/2; })
                        .attr("y", function(d) { return y(d[1])-5; })
                        .attr("text-anchor", "middle");

                    function mouseover(d){  // utility function to be called on mouseover.
                        // filter for selected state.
                        var st = fData.filter(function(s){ return s.l_month == d[0];})[0],
                            nD = d3.keys(st.leave).map(function(s){ return {type:s, leave:st.leave[s]};});

                        // call update functions of pie-chart and legend.
//                        pC.update(nD);
                        leg.update(nD);
                    }

                    function mouseout(d){    // utility function to be called on mouseout.
                        // reset the pie-chart and legend.
//                        pC.update(tF);
                        leg.update(tF);
                    }

                    // create function to update the bars. This will be used by pie-chart.
                    hG.update = function(nD, color){
                        // update the domain of the y-axis map to reflect change in frequencies.
                        y.domain([0, d3.max(nD, function(d) { return d[1]; })]);

                        // Attach the new data to the bars.
                        var bars = hGsvg.selectAll(".bar").data(nD);

                        // transition the height and color of rectangles.
                        bars.select("rect").transition().duration(500)
                            .attr("y", function(d) {return y(d[1]); })
                            .attr("height", function(d) { return hGDim.h - y(d[1]); })
                            .attr("fill", color);

                        // transition the frequency labels location and change value.
                        bars.select("text").transition().duration(500)
                            .text(function(d){ return d3.format(",")(d[1])})
                            .attr("y", function(d) {return y(d[1])-5; });
                    }
                    return hG;
                }
                // function to handle legend.
                function legend(lD){
                    var leg = {};

                    // create div for legend and add a scrollable container.
                    var legendDiv = d3.select(id).append("div").attr('class', 'legend-container')
                        .style('overflow-y', 'auto')
                        .style('max-height', '200px'); // adjust max-height as needed

                    // create table for legend.
                    var legend = legendDiv.append("table").attr('class','legend');

//                    var leg = {};
//
//                    // create table for legend.
//                    var legend = d3.select(id).append("table").attr('class','legend');
//
//                    // create one row per segment.
                    var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");

                    // create the first column for each segment.
                    tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                        .attr("width", '16').attr("height", '16')
                        .attr("fill", function(d, i){return color(i);})

                    // create the second column for each segment.
                    tr.append("td").text(function(d){ return d.type;});

                    // create the third column for each segment.
                    tr.append("td").attr("class",'legendFreq')
                        .text(function(d){ return d.l_month;});

                    // create the fourth column for each segment.
                    tr.append("td").attr("class",'legendPerc')
                        .text(function(d){ return getLegend(d,lD);});

                    // Utility function to be used to update the legend.
                    leg.update = function(nD){
                        // update the data attached to the row elements.
                        var l = legend.select("tbody").selectAll("tr").data(nD);

                        // update the frequencies.
                        l.select(".legendFreq").text(function(d){ return d3.format(",")(d.leave);});

                        // update the percentage column.
                        l.select(".legendPerc").text(function(d){ return getLegend(d,nD);});
                    }

                    function getLegend(d,aD){ // Utility function to compute percentage.
                        var perc = (d.leave/d3.sum(aD.map(function(v){ return v.leave; })));
                        if (isNaN(perc)){
                            return d3.format("%")(0);
                            }
                        else{
                            return d3.format("%")(d.leave/d3.sum(aD.map(function(v){ return v.leave; })));
                            }
                    }

                    return leg;
                }

                // calculate total frequency by segment for all state.
                var tF = dept.map(function(d){
                    return {type:d, leave: d3.sum(fData.map(function(t){ return t.leave[d];}))};
                });

                // calculate total frequency by state for all segment.
                var sF = fData.map(function(d){return [d.l_month,d.total];});

                var hG = histoGram(sF), // create the histogram.
                    leg= legend(tF);  // create the legend.
        });
    },

    // Bar Chart NC YC GC OR & RC for Floor
    render_bar_chart_floor: function(){
        var self = this;
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1',
            '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
            '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);

        rpc.query({
                model: "project.floors",
                method: "get_floor_counts",
            }).then(function (data) {
                var fData = data[0];
                var dept = data[1];
                var id = self.$('.floor_graph_count')[0];
                var barColor = '#ff618a';
                // compute total for each state.
                fData.forEach(function(d){
                    var total = 0;
                    for (var dpt in dept){
                        total += d.leave[dept[dpt]];
                    }
                    d.total = total;
                });

                // function to handle histogram.
                function histoGram(fD){
                    var hG={}, hGDim = {t: 60, r: 0, b: 30, l: 0};
                    hGDim.w = 350 - hGDim.l - hGDim.r;
                    hGDim.h = 200 - hGDim.t - hGDim.b;

                    // create svg for histogram.
                    var hGsvg = d3.select(id).append("svg")
                        .attr("width", hGDim.w + hGDim.l + hGDim.r)
                        .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
                        .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");

                    // create function for x-axis mapping.
                    var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
                        .domain(fD.map(function(d) { return d[0]; }));

                    // Add x-axis to the histogram svg.
                    hGsvg.append("g").attr("class", "x axis")
                        .attr("transform", "translate(0," + hGDim.h + ")")
                        .call(d3.svg.axis().scale(x).orient("bottom"));

                    // Create function for y-axis map.
                    var y = d3.scale.linear().range([hGDim.h, 0])
                        .domain([0, d3.max(fD, function(d) { return d[1]; })]);

                    // Create bars for histogram to contain rectangles and freq labels.
                    var bars = hGsvg.selectAll(".bar").data(fD).enter()
                        .append("g").attr("class", "bar");

                    // create the rectangles.
                    bars.append("rect")
                        .attr("x", function(d) { return x(d[0]); })
                        .attr("y", function(d) { return y(d[1]); })
                        .attr("width", x.rangeBand())
                        .attr("height", function(d) { return hGDim.h - y(d[1]); })
                        .attr('fill', barColor)
                        .on("mouseover", mouseover) // mouseover is defined below.
                        .on("mouseout", mouseout); // mouseout is defined below.

                    // create the frequency labels above the rectangles.
                    bars.append("text").text(function(d){ return d3.format(",")(d[1]) })
                        .attr("x", function(d) { return x(d[0]) + x.rangeBand() / 2; })
                        .attr("y", function(d) { return y(d[1]) - 5; })
                        .attr("text-anchor", "middle");

                    function mouseover(d){  // utility function to be called on mouseover.
                        // filter for selected state.
                        var st = fData.filter(function(s){ return s.l_month == d[0]; })[0],
                            nD = d3.keys(st.leave).map(function(s){ return { type: s, leave: st.leave[s] }; });

                        // call update functions of pie-chart and legend.
                        leg.update(nD);
                    }

                    function mouseout(d){    // utility function to be called on mouseout.
                        // reset the pie-chart and legend.
                        leg.update(tF);
                    }

                    // create function to update the bars. This will be used by pie-chart.
                    hG.update = function(nD, color){
                        // update the domain of the y-axis map to reflect change in frequencies.
                        y.domain([0, d3.max(nD, function(d) { return d[1]; })]);

                        // Attach the new data to the bars.
                        var bars = hGsvg.selectAll(".bar").data(nD);

                        // transition the height and color of rectangles.
                        bars.select("rect").transition().duration(500)
                            .attr("y", function(d) { return y(d[1]); })
                            .attr("height", function(d) { return hGDim.h - y(d[1]); })
                            .attr("fill", color);

                        // transition the frequency labels location and change value.
                        bars.select("text").transition().duration(500)
                            .text(function(d){ return d3.format(",")(d[1]) })
                            .attr("y", function(d) { return y(d[1]) - 5; });
                    };
                    return hG;
                }

                // function to handle legend.
                function legend(lD){
                    var leg = {};

                    // create div for legend and add a scrollable container.
                    var legendDiv = d3.select(id).append("div").attr('class', 'legend-container')
                        .style('overflow-y', 'auto')
                        .style('max-height', '200px'); // adjust max-height as needed

                    // create table for legend.
                    var legend = legendDiv.append("table").attr('class','legend');

                    // create one row per segment.
                    var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");

                    // create the first column for each segment.
                    tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                        .attr("width", '16').attr("height", '16')
                        .attr("fill", function(d, i){ return color(i); });

                    // create the second column for each segment.
                    tr.append("td").text(function(d){ return d.type; });

                    // create the third column for each segment.
                    tr.append("td").attr("class", 'legendFreq')
                        .text(function(d){ return d.l_month; });

                    // create the fourth column for each segment.
                    tr.append("td").attr("class", 'legendPerc')
                        .text(function(d){ return getLegend(d, lD); });

                    // Utility function to be used to update the legend.
                    leg.update = function(nD){
                        // update the data attached to the row elements.
                        var l = legend.select("tbody").selectAll("tr").data(nD);

                        // update the frequencies.
                        l.select(".legendFreq").text(function(d){ return d3.format(",")(d.leave); });

                        // update the percentage column.
                        l.select(".legendPerc").text(function(d){ return getLegend(d, nD); });
                    };

                    function getLegend(d, aD){ // Utility function to compute percentage.
                        var perc = (d.leave / d3.sum(aD.map(function(v){ return v.leave; })));
                        if (isNaN(perc)){
                            return d3.format("%")(0);
                        }
                        else{
                            return d3.format("%")(d.leave / d3.sum(aD.map(function(v){ return v.leave; })));
                        }
                    }

                    return leg;
                }

                // calculate total frequency by segment for all states.
                var tF = dept.map(function(d){
                    return {type: d, leave: d3.sum(fData.map(function(t){ return t.leave[d]; }))};
                });

                // calculate total frequency by state for all segments.
                var sF = fData.map(function(d){ return [d.l_month, d.total]; });

                var hG = histoGram(sF), // create the histogram.
                    leg = legend(tF);  // create the legend.
        });
    },
   });

    core.action_registry.add('hr_dashboard', Dashboard);

});
