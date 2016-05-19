# -*- coding: utf-8 -*-
# © <2016> <Jarsa Sistemas, S.A. de C.V.>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models, _
import requests
from lxml import etree
import base64


class CvaConfigSettings(models.TransientModel):
    _name = 'cva.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    name = fields.Char(
        string='Client number', related='company_id.cva_user',
        default=lambda self: self.env.user.company_id.cva_user)
    allowed_groups = fields.Many2many(
        'cva.group',
        related='company_id.cva_group', string='Allowed groups',
        default=lambda self: self.env.user.company_id.cva_group)

    @api.multi
    def set_allowed_groups(self):
        if self.allowed_groups:
            self.company_id.write({'cva_group': self.allowed_groups})

    @api.multi
    def set_name(self):
        if self.name:
            self.company_id.write({'cva_user': self.name})

    @api.multi
    def connect_cva(self, params):
        """
            Connect to CVA web-services
            @param params: dict with parameters to generate xml file
            @return: returns a xml object
        """
        url = (
            'https://www.grupocva.com/catalogo_clientes_xml/lista_precios.xml')
        data = requests.get(str(url), params=params).content
        root = etree.XML(data)
        return root

    @api.multi
    def get_groups(self):
        group = self.env['cva.group']
        group_list = [x.name for x in group.search([])]
        params = {'cliente': self.name}
        root = self.connect_cva(params)
        for item in root:
            if (item.findtext('grupo') not in group_list and
                    item.findtext('grupo') != ''):
                group.create({'name': item.findtext('grupo')})
                group_list.append(item.findtext('grupo'))

    @api.multi
    def create_product(self, item):
        product_obj = self.env['product.template']
        find = item.findtext
        if not find('imagen'):
            image = False
        else:
            image = base64.encodestring(
                requests.get(find('imagen')).content)
        product_obj.create(
            {'name': find('descripcion'),
             'default_code': find('clave'),
             'standard_price': float(find('precio')),
             'description': _('Group\n' + find('grupo') + '\n' +
                              'Subgroup\n' + find('subgrupo') +
                              '\n' + 'Ficha comercial\n' +
                              find('ficha_comercial') +
                              '\n' + 'Ficha tecnica\n' +
                              find('ficha_tecnica')),
             'image_medium': image,
             'type': 'product'
             })

    def update_product_cron(self):
        product = self.env['product.template']
        product_list = [x.default_code for x in product.search([])]
        params = {
            'cliente': self.name,
            'depto': '1',
            'dt': '1',
            'dc': '1',
            'subgpo': '1',
            'MonedaPesos': '1',
        }
        root = self.connect_cva(params)
        for item in root:
            find = item.findtext
            if find('clave') in product_list:
                find = item.findtext
                if not find('imagen'):
                    image = False
                else:
                    image = base64.encodestring(
                        requests.get(find('imagen')).content)
                product.write({
                    'name': find('descripcion'),
                    'default_code': find('clave'),
                    'standard_price': float(find('precio')),
                    'description': _('Group\n' + find('grupo') + '\n' +
                                     'Subgroup\n' + find('subgrupo') +
                                     '\n' + 'Ficha comercial\n' +
                                     find('ficha_comercial') +
                                     '\n' + 'Ficha tecnica\n' +
                                     find('ficha_tecnica')),
                    'image_medium': image,
                    'type': 'product'
                })

        return root

    @api.multi
    def get_products(self):
        product = self.env['product.template']
        group_list = [x.name for x in self.allowed_groups]
        product_list = [x.default_code for x in product.search([])]
        for group in group_list:
            params = {
                'cliente': self.name,
                'grupo': group,
                'depto': '1',
                'dt': '1',
                'dc': '1',
                'subgpo': '1',
                'MonedaPesos': '1',
            }
            root = self.connect_cva(params)
            for item in root:
                find = item.findtext
                if find('clave') not in product_list:
                    self.create_product(item)

            return root
