from xml.etree.ElementTree import parse as parse_xml, Element, ElementTree, SubElement, tostring, indent
from dataclasses import dataclass
from typing import Union
from enum import Enum
from abc import ABC, abstractmethod
import os


def load_aom_xml(ROOT_DIR: str, VERSION: float) -> tuple[ElementTree, ElementTree]:
    '''Loads an XML file and returns an ElementTree'''
    # Retrieve techtree and proto file from root directory
    techtree_file = f'techtree{VERSION}.xml'
    proto_file    = f'proto{VERSION}.xml'

    # Verify that the files exist
    files = os.listdir(ROOT_DIR)
    assert(techtree_file in files)
    assert(proto_file in files)
    print(f'Found {techtree_file} and {proto_file} in {ROOT_DIR}')
    
    # Parse XML files
    techtree = parse_xml(os.path.join(ROOT_DIR, techtree_file))
    proto    = parse_xml(os.path.join(ROOT_DIR, proto_file))
    return techtree, proto

def display_xml_element(element: Element, level=0, multiplier=1, spacer='  '):
    '''Displays an xml element with its attributes'''
    attributes = ' '.join(f'{attr}={element.attrib[attr]}' for attr in element.attrib)
    print(f'(x{multiplier:3d}) {spacer*level}<{element.tag} {attributes}> {element.text.strip() if element.text else ""}')

def display_xml_tree(parent: Union[Element, list[Element]], level=1, max_level=3, multiplier=1, spacer='  '):
    '''Recursive explorer to display the tags of the XML tree'''
    # Unpack elements if its a list
    if isinstance(parent, list):
        for element in parent:
            display_xml_tree(element, level, max_level, multiplier, spacer)
        return
    
    # Display current element and stop execution if level is too deep
    display_xml_element(parent, level, multiplier, spacer)
    if level > max_level: return

    # Extract children tags and sort by occurence
    tags = list(child.tag for child in parent)
    occurences = sorted( [(tags.count(tag), tag) for tag in set(tags)], reverse=True)
    for occurence, tag in occurences:
        display_xml_tree(parent[tags.index(tag)], level+1, multiplier=occurence)

def print_element(element: Element, indentation='  ', max_print_chars=10_000) -> str:
    '''Converts an XML element to a string'''
    if indentation: indent(element, indentation)
    str = tostring(element, encoding='unicode', method='xml')
    print(str[:max_print_chars])

parent_maps_cache: dict[ElementTree, dict[Element, Element]] = {}

def get_parent(tree: ElementTree, element: Element, nth_parent=1) -> Element:
    '''Get the nth parent of an element, 1=parent, 2=grandparent, etc.'''
    if tree not in parent_maps_cache:
        parent_maps_cache[tree] = {c:p for p in tree.iter() for c in p}
    parent_map = parent_maps_cache[tree]
    
    for n in range(nth_parent):
        if element not in parent_map:
            return print(f'Element {element.tag} has no parent of level {nth_parent}')
        element = parent_map[element]
    return element


class Age(Enum):
    Archaic = 'Archaic Age'
    Classical = 'Classical Age'
    Heroic = 'Heroic Age'
    Mythic = 'Mythic Age'

class Culture(Enum):
    Greek = 'Greek'
    Egyptian = 'Egyptian'
    Norse = 'Norse'
    Atlantean = 'Atlantean'
    Chinese = 'Chinese'
    
class Relativity(Enum):
    BasePercent = 'BasePercent'
    Absolute = 'Absolute'
    Percent = 'Percent'

@dataclass
class Tech:
    '''Class for generating new tech in the tech tree'''
    techtree: ElementTree
    proto: ElementTree
    name: str
    cost: tuple[int, int, int, int] # food, gold, wood, favor
    researchpoints: int
    
    def generate_tech(self, target_tech_selector: str = 'tech[@name="Watch Tower"]'):
        '''Generates a new tech in the tech tree from a source tech'''
        # Creating the tech element
        self.tech = SubElement(self.techtree.getroot(), 'tech', {'name': self.name, 'type': 'Normal'})
        
        # Copying the source tech identity
        srctech = self.techtree.find(target_tech_selector)
        # SubElement(self.tech, 'dbid').text = ''
        SubElement(self.tech, 'displaynameid' ).text = srctech.find('displaynameid').text
        SubElement(self.tech, 'rollovertextid').text = srctech.find('rollovertextid').text
        SubElement(self.tech, 'icon'          ).text = srctech.find('icon').text
        
        # Injecting the new cost and research points
        if self.cost[0]: SubElement(self.tech, 'cost', {'resourcetype': 'Food'}).text = str(self.cost[0])
        if self.cost[1]: SubElement(self.tech, 'cost', {'resourcetype': 'Gold'}).text = str(self.cost[1])
        if self.cost[2]: SubElement(self.tech, 'cost', {'resourcetype': 'Wood'}).text = str(self.cost[2])
        if self.cost[3]: SubElement(self.tech, 'cost', {'resourcetype': 'Favor'}).text = str(self.cost[3])
        SubElement(self.tech, 'researchpoints').text = str(self.researchpoints)
        
        # Making it active and adding prereqs and effects tags
        SubElement(self.tech, 'status').text = 'OBTAINABLE'
        self.prereqs = SubElement(self.tech, 'prereqs')
        self.hasprereq = False
        self.effects = SubElement(self.tech, 'effects')
        self.haseffects = False
        return self
    
    def _add_prereq(self):
        if self.prereqs is None: raise Exception('Tech has not been generated yet')
        self.hasprereq = True
    
    def add_prereq_tech(self, techname: str):
        '''Add another tech as a prerequisite'''
        self._add_prereq()
        SubElement(self.prereqs, 'techstatus', {'status': 'Active'}).text = techname
        return self
        
    def add_prereq_age(self, age: Age):
        '''Add a specific age as a prerequisite'''
        self._add_prereq()
        SubElement(self.prereqs, 'specificage').text = age.value
        return self
        
    def add_prereq_culture(self, cultures: list[Culture]):
        '''Add a specific set of cultures as a prerequisite'''
        self._add_prereq()
        culture_prereq = SubElement(self.prereqs, 'culture')
        for culture in cultures:
            SubElement(culture_prereq, 'culturename').text = culture
        self.hasprereq = True
        return self

    def add_effect(self, target_unit_selector: str, subtype: str, amount: float, relativity: Relativity, action=None, **kwargs):
        '''Add an effect to the tech'''
        # Retrieve the target and verify the subtype is valid
        target_unit = self.proto.find(target_unit_selector)
        target_unit_name = target_unit.get('name')
        if target_unit_name is None: raise Exception(f'Invalid unit selector {target_unit_selector}')
        
        if action is None:
            # If no action is specified, the effect is applied to the unit attribute directly
            valid_subtypes = [el.tag for el in target_unit]
        else:
            # If an action is specific, the effect is applied to the action attribute
            valid_actions = [el.get('name', '<unnamed>') for el in target_unit.findall('action')]
            if action not in valid_actions:
                raise Exception(f'Invalid action {action} for unit {target_unit_selector}, not in {valid_actions}')
            action_tag = target_unit.find(f'action[@name="{action}"]')
            valid_subtypes = [el.get('name') for el in action_tag if el.get('name') is not None and el.tag == 'param']
        
        # Verify the subtype is valid
        if subtype not in valid_subtypes:
            # Ignore these subtypes as they exists for all units without being defined in the xml
            if subtype not in ('Hitpoints',):
                raise Exception(f'Invalid subtype {subtype} for unit {target_unit_selector}, not in {valid_subtypes}')
        
        # Create the effect element
        if self.effects is None: raise Exception('Tech has not been generated yet')
        effect_attributes = {'type': 'Data', 'subtype': subtype, 'amount': str(amount), 'relativity': relativity.value, **kwargs}
        if action is not None: effect_attributes['action'] = action
        effect = SubElement(self.effects, 'effect', effect_attributes)
        
        # Add the target
        SubElement(effect, 'target', {'type': 'ProtoUnit'}).text = target_unit_name
        self.haseffects = True
        return self

    def add_to_unit_menu(self, target_unit_selector: str, row: int, column: int):
        '''Add the tech to the unit menu'''
        # Retrieve the target unit and add tech
        target_unit = self.proto.find(target_unit_selector)
        SubElement(target_unit, 'tech', {'row': str(row), 'page': '1', 'column': str(column)}).text = self.tech.get('name')
        
        # Remove unused tags if any
        if not self.haseffects:
            print('removing effects')
            self.tech.remove(self.effects)
        if not self.hasprereq: self.tech.remove(self.prereqs)
        return self
    
def export_updated_xml(tree: ElementTree, filename: str):
    '''Export the updated XML tree to a file'''
    indent(tree, space='    ')
    tree.write(filename, encoding='utf-8', xml_declaration=True)


class AOMXMLInjector(ABC):
    def __init__(self, ROOT_DIR: str, VERSION: str):
        self.ROOT_DIR = ROOT_DIR
        self.VERSION = VERSION
        self.techtree, self.proto = load_aom_xml(ROOT_DIR, VERSION)
        self.backup('xml/backup')
        self.inject()
        self.export('xml/export')
        
    def backup(self, backup_dir: str):
        '''Backup the XML files before we overwrite them'''
        export_updated_xml(self.techtree, os.path.join(backup_dir, f'techtree{self.VERSION}.xml'))
        export_updated_xml(self.proto   , os.path.join(backup_dir, f'proto{self.VERSION}.xml'))
        print(f'Successfully backed up XML files to {backup_dir}')
    
    @abstractmethod
    def inject(self):
        '''Injects the techs into the XML files'''
        pass
    
    def export(self, export_dir: str):
        '''Exports the XML files'''
        export_updated_xml(self.techtree, os.path.join(export_dir, f'techtree{self.VERSION}.xml'))
        export_updated_xml(self.proto   , os.path.join(export_dir, f'proto{self.VERSION}.xml'))
        print(f'Successfully exported injected XML files to {export_dir}')
