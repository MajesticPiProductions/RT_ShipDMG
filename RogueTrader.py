import os
import cgi
import urllib
import random
import csv

import jinja2
import webapp2

from google.appengine.ext import ndb

class Result(ndb.Model):
    average_mc = ndb.FloatProperty()
    average_la = ndb.FloatProperty()
    average_marc = ndb.FloatProperty()
    ballistic = ndb.IntegerProperty()
    armour = ndb.IntegerProperty()
    dmg_type = ndb.StringProperty()
    
    @classmethod
    def dmg_query_bs(cls, BS):
        return cls.query(cls.ballistic == BS).order(cls.armour)
    
class Weapon(ndb.Model):
    number = ndb.IntegerProperty()
    type = ndb.StringProperty()
    name = ndb.StringProperty()
    strength = ndb.IntegerProperty()
    dmg_bonus = ndb.IntegerProperty()
    
    @classmethod
    def query_weapon(cls, choice):
        return cls.query(cls.number == choice).fetch()        
    
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def random_roll(die_max=10):
        return int(random.random() * die_max + 1)

def sum_of_multiple_rolls(nr_of_die, die_max=10):
    return sum([random_roll(die_max) for i in range(nr_of_die)])
            
def ToHit(BS, strength):
    Degrees = 0
    tohit = random_roll(100)
    if (tohit <= BS):
        hit = BS - tohit
        Degrees = (hit - hit % 10 + 10) / 10
    if (Degrees > strength):
        Degrees = strength
    return int(Degrees);
    
def DMG_mc(dmg, deg, arm):
    sum = sum_of_multiple_rolls(deg)+deg*dmg-arm
    if (sum < 0):
        sum = 0
    return sum;
    
def DMG_la(dmg, deg, arm):
    sum = sum_of_multiple_rolls(deg)+deg*dmg
    if (sum < 0):
        sum = 0
    return sum;
        
def DMG_marc(dmg, deg, arm):
    total = 0
    sum = 0
    while (deg > 0):
        deg -= 1
        tmp = random_roll(10) + dmg - arm + 12
        if (tmp > 0):
            sum += tmp
    return sum;
        
class MainPage(webapp2.RequestHandler):

    def get(self):
        ndb.delete_multi(Result.query().fetch(keys_only=True))
        weapons = Weapon.query().order(Weapon.number)
        template_values = {
            'weapons': weapons,
        }
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))
    
class CalcPage(webapp2.RequestHandler):

    def post(self):
        BSu = int(self.request.get('BSu'))
        BSl = int(self.request.get('BSl'))
        interval = int(self.request.get('Interval'))
        if (interval < 1): interval = 1
        choice = int(self.request.get('choice'))
        chosen_test = Weapon.query(Weapon.number == choice).fetch(1)
        
        for property in chosen_test:
            name = property.name
            type = property.type
            strength = int(property.strength)
            dmg_bonus = int(property.dmg_bonus)
        
        if (type == 'MC'): chosen_type = 'Macro-Cannon'
        if (type == 'LA'): chosen_type = 'Lance'
        weapon_choice = str(name)+ '-' + chosen_type + '\tStrength: ' + str(strength) + '\tDamage: 1d10+' + str(dmg_bonus)
        
        bs_list = []
        dmg_bonus = int(dmg_bonus)
        bs_count = 0
        while (BSl < (BSu + 1)):
            bs_count += 1
            bs_list.append(BSl)
            armour = 12
            while (armour < 25):
                count = 0.0
                total_dmg_mc = 0.0
                total_dmg_la = 0.0
                total_dmg_marc = 0.0
                while (count < 10000):
                    count += 1
                    deg = ToHit(BSl, strength)
                    if (type == 'MC'):
                        total_dmg_mc += DMG_mc(dmg_bonus, deg, armour)
                        total_dmg_marc += DMG_marc(dmg_bonus, deg, armour)
                    if (type == 'LA'):
                        total_dmg_la += DMG_la(dmg_bonus, deg, armour)
                if (type == 'MC'):
                    result = Result(average_mc = total_dmg_mc/count, average_marc = total_dmg_marc/count, average_la = total_dmg_la/count, armour = armour, ballistic = BSl, dmg_type = type)
                if (type == 'LA'):
                    result = Result(average_la = total_dmg_la/count, armour = armour, ballistic = BSl, dmg_type = type)
                result.put()          
                armour += 1
            BSl += interval
        
        dmg_query = result.query(ndb.AND(Result.armour > 11, ndb.AND(Result.armour < 21))).order(Result.armour)
        
        template_values = {
            'bs_list': bs_list,
            'type': type,
            'dmg_query': dmg_query,
            'weapon_choice': weapon_choice,
        }

        template = JINJA_ENVIRONMENT.get_template('calc.html')
        self.response.write(template.render(template_values))
        
        ndb.delete_multi(Result.query().fetch(keys_only=True))
        
class ChangePage(webapp2.RequestHandler):

    def post(self):
        
        testa = Weapon.query().fetch(keys_only=True)
        weapons = Weapon.query().order(Weapon.number)
        
                        
        template_values = {
            'weapons': weapons,
            'testa': testa,
        }

        template = JINJA_ENVIRONMENT.get_template('change.html')
        self.response.write(template.render(template_values))
        
class Reset(webapp2.RequestHandler):

    def post(self):
        ndb.delete_multi(Weapon.query().fetch(keys_only=True))
        path_to_Cannon_file = "./Weapons.txt"
        cannons_csv = csv.DictReader(open(path_to_Cannon_file, "r"), delimiter=";")
        cannons = {}
        item_counter = 1
        for cannon in cannons_csv:
            cannons[item_counter] = cannon
            weapon = Weapon(number = item_counter, type = cannon['Type'], name = cannon['Name'], strength = int(cannon['Strength']), dmg_bonus = int(cannon['DamageBonus']))
            weapon.put()
            item_counter += 1
            
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('done.html')
        self.response.write(template.render(template_values))
        
class NewWeapon(webapp2.RequestHandler):

    def post(self):
        new_type = str(self.request.get('new_type'))
        new_name = str(self.request.get('new_name'))
        new_strength = int(self.request.get('new_strength'))
        new_dmg_bonus = int(self.request.get('new_dmg_bonus'))
        
        weapons = Weapon.query().order(Weapon.number)
        for weapon in weapons:
            new_number = weapon.number
        new_number += 1
        
        new_weapon = Weapon(
                    number = int(new_number),
                    type = new_type,
                    name = new_name,
                    strength = int(new_strength),
                    dmg_bonus = int(new_dmg_bonus))
        new_weapon.put()
        
        template_values = {
        }
        template = JINJA_ENVIRONMENT.get_template('done.html')
        self.response.write(template.render(template_values))
 
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/calc', CalcPage),
    ('/change', ChangePage),
    ('/reset', Reset),
    ('/new_weapon', NewWeapon)
], debug=True)