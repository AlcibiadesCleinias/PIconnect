"""Core containers for connections to the PI Asset Framework."""
from PIthon.AFSDK import AF
from PIthon.PIData import PISeries, PISeriesContainer
from PIthon._operators import add_operators, operators


class PIAFDatabase(object):
    """Context manager for connections to the PI Asset Framework database."""
    version = '0.1.0'

    servers = {x.Name: {'server': x, 'databases': {}} for x in AF.PISystems()}
    default_server = servers[AF.PISystems().DefaultPISystem.Name]

    def __init__(self, server=None, database=None):
        server = self.servers.get(server, self.default_server)
        self.server = server['server']
        if not server['databases']:
            server['databases'] = {x.Name: x for x in self.server.Databases}
        self.database = server['databases'].get(database,
                                                self.server.Databases.DefaultDatabase)

    def __enter__(self):
        self.server.Connect()
        return self

    def __exit__(self, *args):
        self.server.Disconnect()

    def __repr__(self):
        return u'%s(\\\\%s\\%s)' % (self.__class__.__name__,
                                    self.server_name,
                                    self.database_name)

    @property
    def server_name(self):
        """Return the name of the connected PI AF server."""
        return self.server.Name

    @property
    def database_name(self):
        """Return the name of the connected PI AF database."""
        return self.database.Name

    @property
    def children(self):
        """Return a dictionary of the direct child elements of the database."""
        return {c.Name: PIAFElement(c) for c in self.database.Elements}

    def descendant(self, path):
        """Return a descendant of the database from an exact path."""
        return PIAFElement(self.database.Elements.get_Item(path))


class PIAFElement(object):
    """Container for PI AF elements in the database."""
    version = '0.1.0'

    def __init__(self, element):
        self.element = element

    def __repr__(self):
        return u'%s(%s)' % (self.__class__.__name__, self.name)

    @property
    def name(self):
        """Return the name of the current element."""
        return self.element.Name

    @property
    def parent(self):
        """Return the parent element of the current element, or None if it has none."""
        if not self.element.Parent:
            return None
        return self.__class__(self.element.Parent)

    @property
    def children(self):
        """Return a dictionary of the direct child elements of the current element."""
        return {c.Name: self.__class__(c) for c in self.element.Elements}

    def descendant(self, path):
        """Return a descendant of the current element from an exact path."""
        return self.__class__(self.element.Elements.get_Item(path))

    @property
    def attributes(self):
        """Return a dictionary of the attributes of the current element."""
        return {a.Name: PIAFAttribute(self, a) for a in self.element.Attributes}


@add_operators(
    operators=operators,
    members=[
        '_current_value',
        'sampled_data'
    ],
    newclassname='VirtualPIPoint',
    attributes=['pi_point']
)
class PIAFAttribute(PISeriesContainer):
    """Container for attributes of PI AF elements in the database."""
    version = '0.0.1'

    def __init__(self, element, attribute):
        self.element = element
        self.attribute = attribute

    def __repr__(self):
        return u'%s(%s, %s; Current Value: %s %s)' % (self.__class__.__name__,
                                                      self.name,
                                                      self.description,
                                                      self.current_value,
                                                      self.units_of_measurement)

    @property
    def name(self):
        """Return the name of the current attribute."""
        return self.attribute.Name

    @property
    def parent(self):
        """Return the parent attribute of the current attribute, or None if it has none."""
        if not self.attribute.Parent:
            return None
        return self.__class__(self.element, self.attribute.Parent)

    @property
    def children(self):
        """Return a dictionary of the direct child attributes of the current attribute."""
        return {a.Name: self.__class__(self.element, a) for a in self.attribute.Attributes}

    @property
    def description(self):
        """Return the description of the PI Point."""
        return self.attribute.Description

    @property
    def current_value(self):
        """Return the current value of the attribute."""
        return self.attribute.GetValue().Value

    @property
    def last_update(self):
        """Return the time at which the current_value was last updated."""
        return PISeries.timestamp_to_index(self.attribute.GetValue().Timestamp.UtcTime)

    @property
    def units_of_measurement(self):
        """Return the units of measurement in which values for this element are reported."""
        return self.attribute.DefaultUOM

    def _recorded_values(self, time_range, boundary_type, filter_expression):
        include_filtered_values = False
        return self.attribute.Data.RecordedValues(time_range,
                                                  boundary_type,
                                                  self.attribute.DefaultUOM,
                                                  filter_expression,
                                                  include_filtered_values)
