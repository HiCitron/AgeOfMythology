import os
from typing import Union
from xml.etree.ElementTree import parse as parse_xml, Element, ElementTree, SubElement, fromstring

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

