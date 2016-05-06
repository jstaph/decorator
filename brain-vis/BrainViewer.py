import csv
import math
from collections import defaultdict
import time

from sys import platform as _platform
import weakref
import cProfile
import pprint
import const

import community as cm
try:
    # ... reading NIfTI 
    import nibabel as nib
    import numpy as np
    # import h5py
    # ... graph drawing
    import networkx as nx

except:
    print "Couldn't import all required packages. See README.md for a list of required packages and installation instructions."
    raise

### BrainViewer packages
from CorrelationTables.correlation_table import CorrelationTable, \
CorrelationTableDisplay, CommunityCorrelationTableDisplay

from QuantData.quantTable import quantTable
from QuantData.quantData import QuantData
from VisitInterface.color_table import CreateColorTable
from VisitInterface.visit_interface import ParcelationPlot, BrainTemplatePlot
from VisitInterface.slice_viewer import *
from GraphInterface.Graph_interface import GraphWidget
from GraphInterface.GraphDataStructure import GraphVisualization
from General_Interface.Layout_interface import LayoutInit
from UIFiles.ProcessUi import ProcessQuantTable

"""
This is the main classless interface that talks to all other modules
I found this implementation to be easier to follow for others
"""

#Loading UI Files
loader = QUiLoader()

CURR = os.environ['PYTHONPATH']
ui = loader.load(os.path.join(CURR, "UIFiles/interface.ui"))
dataSetLoader = loader.load(os.path.join(CURR, "UIFiles/datasetviewer.ui"))
screenshot = loader.load(os.path.join(CURR, "UIFiles/screeshot.ui"))

### MAIN

# PARAMETERS
colorTableName = 'blue_lightblue_red_yellow'
selectedColor = (0, 100, 0, 255)

CorrelationTableShowFlag = True 
MainWindowShowFlag = True
GraphWindowShowFlag = True
ElectrodeWindowShowFlag = False

print "Files"
execfile('BrainViewerDataPaths.py')

print "Reading NII files."
template_data = nib.load(template_filename).get_data().astype(np.uint32)
parcelation_data = nib.load(parcelation_filename).get_data()

print "Creating correlation table display."
correlationTable = CorrelationTable(matrix_filename,centres_abbreviation)

# colorTable = LinearColorTable();
colorTable = CreateColorTable(colorTableName)
colorTable.setRange(correlationTable.valueRange())

print "Setting up VisIt plots."
brainTemplatePlot = BrainTemplatePlot(template_data)
parcelationPlot = ParcelationPlot(parcelation_data, centre_filename, correlationTable, colorTable, selectedColor)

print "Creating main GUI."
Counter = len(correlationTable.data)
DataColor = np.zeros(Counter+1)

if Counter < 50:
        Offset= Counter/2 - Counter/28
else: 
        Offset = 4

main = QtGui.QWidget()
main.setSizePolicy(QtGui.QSizePolicy.Policy.Expanding, QtGui.QSizePolicy.Policy.Expanding)
mainLayout = QtGui.QHBoxLayout()
main.setLayout(mainLayout)
main.setContentsMargins(0,0,0,0)

# initializing all thea layouts in the applicaiton 
# Layout for the tablewidget 
BoxTableWidget =QtGui.QWidget()

# Layout for the graph widget 
BoxGraphWidget =QtGui.QWidget()

# Layout for the electrode
BoxElectrodeWidget = QtGui.QWidget() 

allViewersLayout = QtGui.QVBoxLayout()
viewersLayout2 = QtGui.QHBoxLayout()

mainLayout.addLayout(allViewersLayout)
mainLayout.setContentsMargins(0,0,0,0)

viewersLayout1 = QtGui.QHBoxLayout()
allViewersLayout.addLayout(viewersLayout1)
allViewersLayout.setContentsMargins(0,0,0,0)

allViewersLayout.addLayout(viewersLayout2)
allViewersLayout.setContentsMargins(0,0,0,0)


print "Setting Slice Views"
slice_views = [None, None, None]
slice_views[0] = SliceViewer(template_data, parcelation_data, 0, correlationTable, colorTable, selectedColor)
viewersLayout1.addWidget(slice_views[0])
viewersLayout1.setContentsMargins(0,0,0,0)

slice_views[0].sliceChanged.connect(brainTemplatePlot.setThreeSliceX)
slice_views[0].regionSelected.connect(parcelationPlot.colorRelativeToRegion)


slice_views[1] = SliceViewer(template_data, parcelation_data, 1, correlationTable, colorTable, selectedColor)
viewersLayout1.addWidget(slice_views[1])
viewersLayout1.setContentsMargins(0,0,0,0)

slice_views[1].sliceChanged.connect(brainTemplatePlot.setThreeSliceY)
slice_views[1].regionSelected.connect(parcelationPlot.colorRelativeToRegion)


slice_views[2] = SliceViewer(template_data, parcelation_data, 2, correlationTable, colorTable, selectedColor)
viewersLayout2.addWidget(slice_views[2])
viewersLayout2.setContentsMargins(0,0,0,0)

slice_views[2].sliceChanged.connect(brainTemplatePlot.setThreeSliceZ)
slice_views[2].regionSelected.connect(parcelationPlot.colorRelativeToRegion)
slice_views[2].setMinimumSize(250, 250)

print "Setting Graph data GraphDataStructure"
Tab_2_AdjacencyMatrix = GraphVisualization(correlationTable.data)

print "Setting CorrelationTable for communities"
Tab_2_CorrelationTable = CommunityCorrelationTableDisplay(correlationTable, colorTable,Tab_2_AdjacencyMatrix)
Tab_2_CorrelationTable.selectedRegionChanged.connect(parcelationPlot.colorRelativeToRegion)
Tab_2_CorrelationTable.setMinimumSize(390, 460)

print "Setting CorrelationTable"

Tab_1_CorrelationTable = CorrelationTableDisplay(correlationTable, colorTable,Tab_2_AdjacencyMatrix)
Tab_1_CorrelationTable.selectedRegionChanged.connect(parcelationPlot.colorRelativeToRegion)
Tab_1_CorrelationTable.setMinimumSize(390, 460)
Tab_2_CorrelationTable.show()


print "Setting Graph Widget"

""" Controlling graph widgets  """
widget = GraphWidget(Tab_2_AdjacencyMatrix,Tab_2_CorrelationTable,correlationTable,colorTable,selectedColor,BoxGraphWidget,BoxTableWidget,Offset,ui)

Tab_1_CorrelationTable.selectedRegionChanged.connect(widget.NodeSelected)
Tab_1_CorrelationTable.selectedRegionChanged.connect(Tab_2_CorrelationTable.selectRegion)
Tab_2_CorrelationTable.selectedRegionChanged.connect(Tab_1_CorrelationTable.selectedRegionChanged)

""" Controlling Quant Table """

# the solvent data ...
quantData=QuantData(widget)
widget.ThresholdChange.connect(quantData.ThresholdChange)

quantTableObject = quantTable(quantData,widget)
quantData.DataChange.connect(quantTableObject.setTableModel)

print "Setting Graph interface"

Graph_Layout=LayoutInit(widget,quantTableObject,ui,dataSetLoader,screenshot,matrix_filename,centre_filename,centres_abbreviation,template_filename,parcelation_filename,\
    Brain_image_filename,Electrode_Ids_filename,SelectedElectrodes_filename,Electrode_data_filename,Electrode_mat_filename)

widget.regionSelected.connect(parcelationPlot.colorRelativeToRegion)
widget.regionSelected.connect(Tab_1_CorrelationTable.selectRegion)
widget.CommunityColor.connect(parcelationPlot.setRegionColors)
widget.regionSelected.connect(Tab_2_CorrelationTable.selectRegion)

widget.show()

visitViewerLayout = QtGui.QVBoxLayout()
viewersLayout2.addLayout(visitViewerLayout)

"""Window for correlation Table"""
window_CorrelationTable =QtGui.QWidget()
Box = QtGui.QHBoxLayout()
Box.addWidget(Tab_1_CorrelationTable)
Box.setContentsMargins(0, 0, 0, 0)

window_CorrelationTable.setLayout(Box)
window_CorrelationTable.setWindowTitle("CorrelationTable")

window_CorrelationTable.resize(Offset*(Counter)-0,Offset*(Counter)+170)

Tab_2_CorrelationTable.hide()
BoxTable = QtGui.QHBoxLayout()
BoxTable.setContentsMargins(0, 0, 0, 0)
BoxTable.addWidget(window_CorrelationTable)
BoxTable.addWidget(Tab_2_CorrelationTable)
BoxTable.addWidget(widget.wid)
BoxTable.setContentsMargins(0, 0, 0, 0)

BoxTableWidget.setLayout(BoxTable)


if CorrelationTableShowFlag:
    BoxTableWidget.show()
    # pass

print "Setting Graph Layout_interface"

Graph = QtGui.QHBoxLayout()
Graph.setContentsMargins(0, 0, 0, 0)
Graph.addWidget(widget.wid)
Graph.addWidget(Graph_Layout)
Graph.setContentsMargins(0, 0, 0, 0)

BoxGraphWidget.setLayout(Graph)

if GraphWindowShowFlag:
    BoxGraphWidget.show()

"""Window for correlation Table"""

print "Setting Visit Plot" 

widget.CommunityColorAndDict.connect(Tab_1_CorrelationTable.setRegionColors)
widget.CommunityColorAndDict.connect(Tab_2_CorrelationTable.setRegionColors)
widget.CommunityMode.connect(parcelationPlot.Community)

# sys.exit(app.exec_())

# Code clicking the group button in the slide
def buttonGroupClicked(number):
    buttons = buttonGroup.buttons()
    for button in buttons:
        if buttonGroup.button(number) != button:
            button.setChecked(False)
        else:
            if button.isChecked() == False: 
                button.setChecked(True)
                return
    if number == -2: 
        parcelationPlot.setCentroidMode()
    else:
        parcelationPlot.setRegionMode()

# Laying out the group buttons in visit plot
box = QtGui.QHBoxLayout()
buttonGroup = QtGui.QButtonGroup()
buttonGroup.setExclusive(True)
buttonGroup.buttonClicked[int].connect(buttonGroupClicked)

r0=QtGui.QRadioButton("Centroids")
r1=QtGui.QRadioButton("Regions")
r1.setChecked(True)
r0.clicked.connect(parcelationPlot.setCentroidMode)
r1.clicked.connect(parcelationPlot.setRegionMode)

buttonGroup.addButton(r0)
buttonGroup.addButton(r1)
box.addWidget(r0)
box.addWidget(r1)

for sv in slice_views:
    widget.regionSelected.connect(sv.colorRelativeToRegion)
    Tab_1_CorrelationTable.selectedRegionChanged.connect(sv.colorRelativeToRegion)
    sv.regionSelected.connect(Tab_1_CorrelationTable.selectRegion)
    sv.regionSelected.connect(Tab_2_CorrelationTable.selectRegion)
    sv.regionSelected.connect(widget.NodeSelected)

    for sv_other in slice_views:
        if sv == sv_other:
            continue 
        sv.regionSelected.connect(sv_other.colorRelativeToRegion)
        
    widget.CommunityColor.connect(sv.setRegionColors)
    widget.CommunityMode.connect(sv.Community)

rwin2 = pyside_support.GetRenderWindow(1)
rwin2.setMinimumSize(100, 100)

visitViewerLayout.addWidget(rwin2)
visitViewerLayout.setContentsMargins(0,0,0,0)
visitViewerLayout.addLayout(box)
visitViewerLayout.setContentsMargins(0,0,0,0)

visitControlsLayout = QtGui.QHBoxLayout()
visitViewerLayout.addLayout(visitControlsLayout)
visitViewerLayout.setContentsMargins(0,0,0,0)

toggleThreeSliceButton = QtGui.QPushButton("Show/Hide Slices")
visitControlsLayout.addWidget(toggleThreeSliceButton)
toggleThreeSliceButton.clicked.connect(brainTemplatePlot.toggleThreeSlice)
toggleBrainSurfaceButton = QtGui.QPushButton("Show/Hide Brain Surfaces")

visitControlsLayout.addWidget(toggleBrainSurfaceButton)
visitControlsLayout.setContentsMargins(0,0,0,0)
toggleBrainSurfaceButton.clicked.connect(brainTemplatePlot.toggleBrainSurface)
pickButton = QtGui.QPushButton("Pick Region")

visitControlsLayout.addWidget(pickButton)
visitControlsLayout.setContentsMargins(0,0,0,0)

pickButton.clicked.connect(parcelationPlot.startPick3D)
parcelationPlot.regionSelected.connect(Tab_1_CorrelationTable.selectRegion)
parcelationPlot.regionSelected.connect(widget.NodeSelected)
parcelationPlot.regionSelected.connect(Tab_2_CorrelationTable.selectRegion)

if MainWindowShowFlag:
    main.show()
