import vtk
from vtk.util import numpy_support
import os
import numpy

import vtk
from numpy import *
import nibabel as nib
import numpy as np
import csv

import pprint
import sys
import PySide
from PySide import QtCore, QtGui
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk.qt.QVTKRenderWindowInteractor import *

class MouseInteractorHighLightActor(vtk.vtkInteractorStyleTrackballCamera):

	def __init__(self,VolumneRendererWindow, selectedColor, PixX, PixY, PixZ):
		super(MouseInteractorHighLightActor, self).__init__()

		self.selectedColor = selectedColor
		self.VolumneRendererWindow = VolumneRendererWindow

		self.AddObserver("LeftButtonPressEvent",self.leftButtonPressEvent)

		self.PixX = PixX
		self.PixY = PixY
		self.PixZ = PixZ
		self.LastPickedActor = None
		self.LastPickedProperty = vtk.vtkProperty()

	def leftButtonPressEvent(self,obj,event):
		clickPos = self.GetInteractor().GetEventPosition()
		pos = self.GetInteractor().GetPicker().GetPickPosition()
		picker = vtk.vtkPropPicker()
		picker.Pick(clickPos[0], clickPos[1], 0, self.GetDefaultRenderer())
		# get the new
		self.NewPickedActor = picker.GetActor()
		"""
		Idea is to compare the xyz locations with the numpy parcels to get the 
		selected Id 
		"""


		# If something was selected
		if self.NewPickedActor:
			# If we picked something before, reset its property
			if self.LastPickedActor:
				self.LastPickedActor.GetProperty().DeepCopy(self.LastPickedProperty)
			# Save the property of the picked TemplateActor so that we can
			# restore it next time
			self.LastPickedProperty.DeepCopy(self.NewPickedActor.GetProperty())
			# Highlight the picked TemplateActor by changing its properties
			# self.NewPickedActor.GetProperty().SetColor(self.selectedColor)
			

			bounds= self.NewPickedActor.GetBounds()  
			if self.VolumneRendererWindow.setCentroidModeFlag: 
				if self.VolumneRendererWindow.SphereActors:
					index = 0
					for actor in self.VolumneRendererWindow.SphereActors:
						if actor == self.NewPickedActor:
							break
						index +=1
					self.VolumneRendererWindow.RegionSelectedIn(index)
			else:
				if self.VolumneRendererWindow.Parcel: 
					index = 0
					for actor in self.VolumneRendererWindow.Parcel:
						if actor == self.NewPickedActor:
							break
						index +=1
					self.VolumneRendererWindow.RegionSelectedIn(index-1)
			# self.NewPickedActor.GetProperty().SetDiffuse(1.0)
			# self.NewPickedActor.GetProperty().SetSpecular(0.0)
			# save the last picked TemplateActor
			self.LastPickedActor = self.NewPickedActor
 
		self.OnLeftButtonDown()
		return

# A simple function to be called when the user decides to quit the application.
def exitCheck(obj, event):
	if obj.GetEventPending() != 0:
		obj.SetAbortRender(1)

class VolumneRendererWindow(PySide.QtGui.QWidget):
	regionSelected = QtCore.Signal(int)

	def __init__(self,parcelation_filename, template_filename,correlationTable,selectedColor,colorTable,SliceX,SliceY,SliceZ):
		super(VolumneRendererWindow,self).__init__()

		self.correlationTable = correlationTable

		self.nRegions = len(self.correlationTable.header)
		self.selectedColor = selectedColor

		self.widget = None
		self.SliceX = SliceX
		self.SliceY = SliceY
		self.SliceZ = SliceZ

		self.colorTable = colorTable
		self.region_data = nib.load(parcelation_filename).get_data().astype(np.uint32)
		self.Centroid = dict()

		self.regionPlotId = -1
		self.centroidPlotId = -1
		self.activePlotId = -1

		self.activePlotId = self.regionPlotId

		self.parcelation_filename = parcelation_filename
		self.template_filename = template_filename

		self.setCentreFilename()

		self.frame = QtGui.QFrame()
		self.BoxLayoutView = QtGui.QVBoxLayout()

		self.BoxLayoutView.setContentsMargins(0, 0, 0, 0)
		self.setLayout(self.BoxLayoutView)
		self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)

		self.setDataset()
		self.setFlags()
		self.RenderData()

		# Create source
		source = vtk.vtkSphereSource()
		source.SetCenter(0, 0, 0)
		source.SetRadius(5.0)

		self.FinalRenderView() 
		self.show()

	def setCentreFilename(self):
		"""
		Logic to check whether there is a filename, if there is 
		just load the file otherwise make sure that a new file is generated 
		which is very much dataset specific 
		"""

		self.CentrePath = os.environ['PYTHONPATH'].split(os.pathsep)
		head, tail = os.path.split(self.parcelation_filename)
		tail = tail.replace(".","") 
		CenterFile = '%s%s'% (str(tail),str('CentreFile.csv'))
		self.CentrePath[0]+='/CentreData/'+CenterFile

		if os.path.isfile(self.CentrePath[0]):
			self.centroidFilename = self.CentrePath[0]
			with open(self.CentrePath[0],'rb') as f:
				r = csv.reader(f, delimiter=' ')
				for index,row in enumerate(r):
					self.Centroid[index] = row
		else:
			print "No Centre File Detected,\nComputing Centres for the Parcelation Plot\nPlease Wait"
			i,j,k = np.shape(self.region_data)
			Centroid = dict()
			counter = 0
			cx=0
			cy=0
			cz=0
			for q in range(i):
				for w in range(j):
					for e in range(k):
						value = self.region_data[q,w,e]
						try:
							if value>0:
								Centroid[value]
							else:
								continue
						except KeyError:
							Centroid[value] = ((0,0,0),0)
						Centroid[value] = ((Centroid[value][0][0]+q,Centroid[value][0][1]+w,Centroid[value][0][2]+e),Centroid[value][1]+1)

			NewChanges = dict()

			# Warning the parcel centres are converted to integer values, this might \
			#affect the uncertaininty associated with the visualization
			for i,j in Centroid.iteritems():
				Centroid[i] = (int(j[0][0]/j[1]), int(j[0][1]/j[1]), int(j[0][2]/j[1]), 1)

			with open(self.CentrePath[0],'wb') as f:
				w = csv.writer(f, delimiter=' ')
				for i,j in Centroid.iteritems():
					w.writerow([int(j[0]),int(j[1]),int(j[2])])
			self.Centroid = Centroid
			self.centroidFilename = self.CentrePath[0]

	def setFlags(self):
		self.setCentroidModeFlag = False
		self.toggleBrainSurfaceFlag = True
		self.toggleThreeSlicesFlag = True
		self.communityMode = False
		self.PickingFlag = True
		self.MapMetrics = False
		self.SphereActors = []
		self.Parcel = []
		self.Slices = [None,None,None]
		self.region_colors = None

		self.SetXAxisValues = 0 
		self.SetYAxisValues = 0 
		self.SetZAxisValues = 0 
		#PixelDimensions Spacing
		self.PixX = 0
		self.PixY = 0
		self.PixZ = 0

	def ColorParcelationPoints(self,x,y,z):
		self.Parcelation

	def setDataset(self): 
		self.ParcelationReader = vtk.vtkNIFTIImageReader()
		self.ParcelationReader.SetFileName(self.parcelation_filename)
		self.ParcelationNumpy = nib.load(self.parcelation_filename).get_data().astype(np.uint8)
		self.ParcelationReader.Update()

		self.TemplateReader = vtk.vtkNIFTIImageReader()
		self.TemplateReader.SetFileName(self.template_filename)
		self.TemplateMapToColors = vtk.vtkImageMapToColors()
		self.TemplateNumpy = nib.load(self.template_filename).get_data().astype(np.uint8)
		self.TemplateReader.Update()

		self.ParcelationNumpy = []
		self.TemplateNumpy = []

		self.Templatedmc =vtk.vtkDiscreteMarchingCubes()
		self.dmc =vtk.vtkDiscreteMarchingCubes()

		self.Template = vtk.vtkPolyData()

		self.appendFilter = vtk.vtkAppendPolyData()
		self.cleanFilter = vtk.vtkCleanPolyData()

		self.mapper = vtk.vtkPolyDataMapper()
		self.TemplateMapper = vtk.vtkPolyDataMapper()

		self.mapper2 = vtk.vtkPolyDataMapper()

		self.outline = vtk.vtkOutlineFilter()

		self.TemplateActor = vtk.vtkActor()
		self.OutlineActor = vtk.vtkActor()

		self.renderer = vtk.vtkRenderer()

		self.renderer.SetBackground(1, 1, 1)

		self.renderWin = vtk.vtkRenderWindow()
		self.renderWin.AddRenderer(self.renderer)

		self.axes2 = vtk.vtkCubeAxesActor2D()
		self.axes3 = vtk.vtkCubeAxesActor2D()

		self.nc = vtk.vtkNamedColors()

		self.lut = vtk.vtkLookupTable()
		self.lut.SetNumberOfTableValues(self.nRegions)
		self.lut.Build()

		self.colorData = vtk.vtkUnsignedCharArray()
		self.colorData.SetName('colors') # Any name will work here.
		self.colorData.SetNumberOfComponents(3)

		self.TextProperty = vtk.vtkTextProperty()
		self.TextProperty.SetColor(0,0,0)
		# self.TextProperty.ShadowOn()
		self.TextProperty.SetFontSize(100)

		self.axesActor = vtk.vtkAnnotatedCubeActor()
		self.axes = vtk.vtkOrientationMarkerWidget()

		self.renderInteractor = QVTKRenderWindowInteractor(self,rw=self.renderWin)
		self.BoxLayoutView.addWidget(self.renderInteractor)

		self.points = vtk.vtkPoints()
		self.triangles = vtk.vtkCellArray()

		self.picker = vtk.vtkCellPicker()

		self.template_data = None

	def RegionSelectedIn(self, Id):
		if not(Id == self.nRegions):
			self.colorRelativeToRegion(Id)
			self.regionSelected.emit(Id)

	def RenderData(self):
		self.DefineTemplateDataToBeMapped()
		self.DefineParcelationDataToBeMapped()
		self.setColors()
		self.AppendDatasets()
		self.SetActorsAndOutline()
		self.SetRenderer()
		self.AddAxisActor()
		self.SetAxisValues()

	def MakeLUT(self,tableSize):
		'''
		Make a lookup table from a set of named colors.
		:param: tableSize - The table size
		:return: The lookup table.
		'''
		regionId = 0
		region_colors = [ self.colorTable.getColor(self.correlationTable.value(regionId, i)) for i in range(self.nRegions) ]
		region_colors[regionId] = self.selectedColor

		index = 0 
		for index in range(tableSize):
			data = region_colors[index]
			r= float(data[0])/255
			g=float(data[1])/255
			b=float(data[2])/255
			a=float(data[3])/255
			self.lut.SetTableValue(index,(r,g,b,a))
			index+=1

	def MakeCellData(self,tableSize, lut, colors):
		for i in range(0,tableSize):
			rgb = [0.0,0.0,0.0]
			lut.GetColor(float(i)/(tableSize-1),rgb)
			ucrgb = list(map(int, [x * 255 for x in rgb]))
			colors.InsertNextTuple3(ucrgb[0], ucrgb[1], ucrgb[2])
			s = '['+ ', '.join(['{:0.6f}'.format(x) for x in rgb]) + ']'

	def setColors(self):
		self.MakeLUT(self.nRegions)
		self.MakeCellData(self.nRegions,self.lut,self.colorData)

	def SetAxisValues(self):
		self.axes2.SetInputConnection(self.Templatedmc.GetOutputPort())
		self.axes2.SetCamera(self.renderer.GetActiveCamera())
		self.axes2.SetLabelFormat("%6.4g")
		self.axes2.SetFlyModeToOuterEdges()
		self.axes2.SetAxisTitleTextProperty(self.TextProperty)
		self.axes2.SetAxisLabelTextProperty(self.TextProperty)
		self.axes2.GetProperty().SetColor(0,0,0)
		self.renderer.AddViewProp(self.axes2)

		self.axes3.SetInputConnection(self.Templatedmc.GetOutputPort())
		self.axes3.SetCamera(self.renderer.GetActiveCamera())
		self.axes3.SetLabelFormat("%6.4g")
		self.axes3.SetFlyModeToClosestTriad()
		self.axes3.SetAxisTitleTextProperty(self.TextProperty)
		self.axes3.SetAxisLabelTextProperty(self.TextProperty)
		self.axes3.GetProperty().SetColor(0,0,0)
		self.renderer.AddViewProp(self.axes3)

	def FinalRenderView(self):
		# Tell the application to use the function as an exit check.
		self.renderWin.AddObserver("AbortCheckEvent", exitCheck)
		self.renderInteractor.Initialize()
		self.renderWin.Render()
		self.renderInteractor.Start()

	def DefineTemplateDataToBeMapped(self):

		self.Templatedmc.SetInputConnection(self.TemplateReader.GetOutputPort())
		self.Templatedmc.Update()

		self.template_data = self.Templatedmc.GetOutput()

	def DefineParcelationDataToBeMapped(self):
		self.PixX = self.ParcelationReader.GetNIFTIHeader().GetPixDim(1)
		self.PixY = self.ParcelationReader.GetNIFTIHeader().GetPixDim(2)
		self.PixZ = self.ParcelationReader.GetNIFTIHeader().GetPixDim(3)
		# Getting the style object to invoke here because we get the real Pix dimensions
		self.style = MouseInteractorHighLightActor(self,self.selectedColor[:3], self.PixX, self.PixY,self.PixZ)
		# self.style.locationRegionSelected.connect(self.locationRegionSelectedIn)		

	def AppendDatasets(self):
		self.TemplateMapper.SetInputConnection(self.Templatedmc.GetOutputPort())
		self.TemplateMapper.ScalarVisibilityOff()

	def SetActorsAndOutline(self):
		self.TemplateActor.SetMapper(self.TemplateMapper)

		# outline
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.outline.SetInputData(self.Templatedmc.GetOutput())
		else:
			self.outline.SetInputConnection(self.Templatedmc.GetOutputPort())

		if vtk.VTK_MAJOR_VERSION <= 5:
			self.mapper2.SetInput(self.outline.GetOutput())
		else:
			self.mapper2.SetInputConnection(self.outline.GetOutputPort())

		self.OutlineActor.SetMapper(self.mapper2)
		self.OutlineActor.GetProperty().SetColor(0,0,0)

		self.TemplateActor.GetProperty().SetColor(1.0, 1.0, 1.0)
		self.TemplateActor.PickableOff()

		self.TemplateActor.GetProperty().SetOpacity(0.1)

		self.renderer.AddViewProp(self.OutlineActor)
		self.renderInteractor.SetRenderWindow(self.renderWin)

	def AddAxisActor(self):
		self.axesActor.SetXPlusFaceText('X')
		self.axesActor.SetXMinusFaceText('X-')
		self.axesActor.SetYMinusFaceText('Y')
		self.axesActor.SetYPlusFaceText('Y-')
		self.axesActor.SetZMinusFaceText('Z')
		self.axesActor.SetZPlusFaceText('Z-')
		self.axesActor.GetTextEdgesProperty().SetColor(1,1,0)
		self.axesActor.GetTextEdgesProperty().SetLineWidth(2)
		self.axesActor.GetCubeProperty().SetColor(0,0,1)
		self.axes.SetOrientationMarker(self.axesActor)
		self.axes.SetInteractor(self.renderInteractor)
		self.axes.EnabledOn()
		self.axes.InteractiveOn()
		self.renderer.ResetCamera()

	def SetRenderer(self):
		# With almost everything else ready, its time to 
		#initialize the renderer and window, as well as 
		#creating a method for exiting the application

		if self.toggleBrainSurfaceFlag:
			self.renderer.AddViewProp(self.TemplateActor)
		else:
			self.renderer.RemoveActor(self.TemplateActor)

		self.addParcels()
		self.addSpheres()
		self.addSlices()

		self.UpdateRenderer()
		self.renderWin.GetInteractor().Render()

	def UpdateRenderer(self):
		if self.toggleBrainSurfaceFlag:
			self.renderer.AddViewProp(self.TemplateActor)
		else:
			self.renderer.RemoveActor(self.TemplateActor)

		if not(self.setCentroidModeFlag): 
			if self.SphereActors:
				self.UpdateSpheres(False)
			self.UpdateParcels(True)
		else: 
			if self.Parcel:
				self.UpdateParcels(False)
			self.UpdateSpheres(True)

		if self.toggleThreeSlicesFlag: 
			self.UpdateSlices(True)
		else: 
			self.UpdateSlices(False)

		if self.PickingFlag:
			# set Picker
			if self.style == None:
				self.style = MouseInteractorHighLightActor(self,self.selectedColor[:3], self.PixX, self.PixY,self.PixZ)
			self.style.SetDefaultRenderer(self.renderer)
			self.renderInteractor.SetInteractorStyle(self.style)	
		else:
			del self.style
			self.style = None
			self.renderInteractor.SetInteractorStyle(self.style)


		# print self.renderer.GetActors().GetLastItem()
		self.renderWin.GetInteractor().Render()


	def UpdateSlices(self,Visibility):
		for actor in self.Slices:
			if Visibility:
				actor.GetProperty().SetOpacity(1)
			else:
				actor.GetProperty().SetOpacity(0)

	def addSlices(self):
		self.addSliceX()
		self.addSliceY()
		self.addSliceZ()

	# def CreateColorImage(self, vtkImageData, NumpyData):

	def setThreeSliceX(self, sliceX):
		self.SetXAxisValues = float(sliceX)*self.PixX
		self.addSliceX()

	def setThreeSliceY(self, sliceY):
		self.SetYAxisValues = float(sliceY)*self.PixY
		self.addSliceY()

	def setThreeSliceZ(self, sliceZ):
		self.SetZAxisValues = float(sliceZ)*self.PixX
		self.addSliceZ()

	def addSliceX(self):
		if not(self.toggleThreeSlicesFlag): 
			return

		# create source
		x, y  = np.shape(self.SliceX.image_data)
		self.SliceX.image_data = np.array(self.SliceX.image_data, dtype=uint16)
		print np.shape(self.SliceX.image_data)






		# dataImporter = vtk.vtkImageImport()

		# if self.SliceX.image_data.dtype == numpy.uint8:
		# 	dataImporter.SetDataScalarTypeToUnsignedChar()
		# elif self.SliceX.image_data.dtype == numpy.uint16:
		# 	dataImporter.SetDataScalarTypeToUnsignedShort()
		# elif self.SliceX.image_data.dtype == numpy.uint32:
		# 	dataImporter.SetDataScalarTypeToInt()
		# elif self.SliceX.image_data.dtype == numpy.int16:
		# 	dataImporter.SetDataScalarTypeToShort()
		# else:
		# 	raise RuntimeError("unknown data type %r of volume" % (self.SliceX.image_data.dtype,))
		
		# if not(self.Slices[0] == None):
		# 	self.renderer.RemoveActor(self.Slices[0])
		# 	self.Slices[0] = None

		# planeSource = vtk.vtkPlane()

		# planeSource.SetOrigin(self.SetXAxisValues,0.0,0.0)
		# planeSource.SetNormal(1.0,0.0,0.0)

		# #create cutter
		# cutter=vtk.vtkCutter()
		# cutter.SetCutFunction(planeSource)
		# cutter.SetInputConnection(self.Templatedmc.GetOutputPort())
		# cutter.Update()
		
		# cutterMapper=vtk.vtkPolyDataMapper()
		# cutterMapper.SetInputConnection(cutter.GetOutputPort())
		# cutterMapper.ScalarVisibilityOn()

		# #create plane actor
		# planeActor=vtk.vtkActor()
		# planeActor.GetProperty().SetColor(1.0,0,0)
		# planeActor.GetProperty().SetLineWidth(2)
		# planeActor.SetMapper(cutterMapper)

		# self.Slices[0] = planeActor

		self.renderer.AddViewProp(planeActor)

		self.renderWin.GetInteractor().Render()

	
	def addSliceY(self):
		if not(self.toggleThreeSlicesFlag): 
			return
		if not(self.Slices[1]== None):
			self.renderer.RemoveActor(self.Slices[1])
			self.Slices[1] = None

		# create source
		x, y  = np.shape(self.SliceY.image_data)
		self.SliceX.image_data = np.array(self.SliceX.image_data, dtype=uint8)

		planeSource = vtk.vtkPlane()

		planeSource.SetOrigin(0.0,self.SetYAxisValues,0.0)
		planeSource.SetNormal(0.0,1.0,0.0)

		#create cutter
		cutter=vtk.vtkCutter()
		cutter.SetCutFunction(planeSource)
		cutter.SetInputConnection(self.Templatedmc.GetOutputPort())
		cutter.Update()
		cutterMapper=vtk.vtkPolyDataMapper()
		cutterMapper.SetInputConnection(cutter.GetOutputPort())
		cutterMapper.ScalarVisibilityOn()

		#create plane actor
		planeActor=vtk.vtkActor()
		planeActor.GetProperty().SetColor(1.0,0,1)
		planeActor.GetProperty().SetLineWidth(2)
		planeActor.SetMapper(cutterMapper)

		self.Slices[1] = planeActor

		self.renderer.AddViewProp(planeActor)
		self.renderWin.GetInteractor().Render()


	def addSliceZ(self):
		if not(self.toggleThreeSlicesFlag): 
			return
		if not(self.Slices[2]== None):
			self.renderer.RemoveActor(self.Slices[2])
			self.Slices[2] = None 

		# create source
		x, y  = np.shape(self.SliceZ.image_data)
		self.SliceX.image_data = np.array(self.SliceX.image_data, dtype=uint8)

		planeSource = vtk.vtkPlane()

		planeSource.SetOrigin(0.0,0.0,self.SetZAxisValues)
		planeSource.SetNormal(0.0,0.0,1.0)

		#create cutter
		cutter=vtk.vtkCutter()
		cutter.SetCutFunction(planeSource)
		cutter.SetInputConnection(self.Templatedmc.GetOutputPort())
		cutter.Update()
		cutterMapper=vtk.vtkPolyDataMapper()
		cutterMapper.SetInputConnection(cutter.GetOutputPort())
		cutterMapper.ScalarVisibilityOn()

		#create plane actor
		planeActor=vtk.vtkActor()
		planeActor.GetProperty().SetColor(1.0,1,0)
		planeActor.GetProperty().SetLineWidth(2)
		planeActor.SetMapper(cutterMapper)

		self.Slices[2] = planeActor

		self.renderer.AddViewProp(planeActor)
		self.renderWin.GetInteractor().Render()


	def removeParcels(self):
		if self.Parcel:
			for actor in self.Parcel:
				self.renderer.RemoveActor(actor)
			del self.Parcel
			self.Parcel = None

	def removeSpheres(self):
		if self.SphereActors:
			for actor in self.SphereActors:
				self.renderer.RemoveActor(actor)
			del self.SphereActors
			self.SphereActors = None

	def addParcels(self):
		self.removeParcels()
		self.Parcel = []
		for i in range(self.nRegions):
			dmc =vtk.vtkDiscreteMarchingCubes()
			dmc.SetInputConnection(self.ParcelationReader.GetOutputPort())
			dmc.GenerateValues(i,i,i)
			dmc.Update()

			mapper = vtk.vtkPolyDataMapper()
			mapper.SetInputConnection(dmc.GetOutputPort())
			mapper.ScalarVisibilityOff()

			actor = vtk.vtkActor()
			actor.SetMapper(mapper)

			if self.region_colors:
				r = float(self.region_colors[i][0])/255
				g = float(self.region_colors[i][1])/255
				b = float(self.region_colors[i][2])/255
			else:
				r= 0.1
				b= 0.1
				g= 0.1

			actor.GetProperty().SetColor(r,g,b)
			# actor.GetProperty().SetDiffuse(.8)
			# actor.GetProperty().SetSpecular(.5)
			actor.GetProperty().SetSpecularColor(1.0,1.0,1.0)
			# actor.GetProperty().SetSpecularPower(30.0)
			self.Parcel.append(actor)
			self.renderer.AddViewProp(actor)

	def addSpheres(self):
		self.removeSpheres()
		self.SphereActors = []
		for i in range(self.nRegions):
			source = vtk.vtkSphereSource()
			# random position and radius
			x = float(self.Centroid[i][0])* self.PixX 
			y = float(self.Centroid[i][1])* self.PixY 
			z = float(self.Centroid[i][2])* self.PixZ 
			
			radius = 5

			source.SetRadius(radius)
			source.SetCenter(x,y,z)

			mapper = vtk.vtkPolyDataMapper()
			mapper.SetInputConnection(source.GetOutputPort())
			mapper.ScalarVisibilityOff()

			actor = vtk.vtkActor()
			actor.SetMapper(mapper)

			if self.region_colors:
				r = float(self.region_colors[i][0])/255
				g = float(self.region_colors[i][1])/255
				b = float(self.region_colors[i][2])/255
			else:
				r= 0.1
				b= 0.1
				g= 0.1
			actor.GetProperty().SetColor(r, g, b)
			actor.GetProperty().SetSpecularColor(1.0,1.0,1.0)
			self.SphereActors.append(actor)
			self.renderer.AddViewProp(actor)

	def UpdateSpheres(self, Visibility):
		for i in range(self.nRegions):
			if self.SphereActors:
				actor = self.SphereActors[i]
				if not(Visibility): 
					actor.GetProperty().SetOpacity(0)
					continue
			if self.region_colors:
				r = float(self.region_colors[i][0])/255
				g = float(self.region_colors[i][1])/255
				b = float(self.region_colors[i][2])/255
			else:
				r= 0.1
				b= 0.1
				g= 0.1

			actor.GetProperty().SetColor(r, g, b)
			actor.GetProperty().SetSpecularColor(1.0,1.0,1.0)
			actor.GetProperty().SetOpacity(1)
		self.renderWin.GetInteractor().Render()

	def UpdateParcels(self,Visibility):
		for i in range(self.nRegions):
			if self.Parcel:
				actor = self.Parcel[i]
				if not(Visibility): 
					actor.GetProperty().SetOpacity(0)
					continue
			if self.region_colors:
				r = float(self.region_colors[i-1][0])/255
				g = float(self.region_colors[i-1][1])/255
				b = float(self.region_colors[i-1][2])/255
			else:
				r= 0.1
				b= 0.1
				g= 0.1
			actor.GetProperty().SetColor(r, g, b)
			actor.GetProperty().SetOpacity(1)
			# actor.GetProperty().SetDiffuse(.8)
			# actor.GetProperty().SetSpecular(.5)
			actor.GetProperty().SetSpecularColor(1.0,1.0,1.0)
			# actor.GetProperty().SetSpecularPower(30.0)

		self.renderWin.GetInteractor().Render()

	"""
	Interactive slots that need the help of an external caller method 
	"""
	def setCentroidMode(self):
		self.setCentroidModeFlag = True
		self.UpdateRenderer()

	def setRegionMode(self):
		self.setCentroidModeFlag = False
		self.UpdateRenderer()

	def	toggleBrainSurface(self):	
		self.toggleBrainSurfaceFlag = not(self.toggleBrainSurfaceFlag)
		self.UpdateRenderer()

	def	toggleThreeSlice(self):
		self.toggleThreeSlicesFlag = not(self.toggleThreeSlicesFlag)
		self.UpdateRenderer()

	# def	EnablePicking(self):
	# 	self.PickingFlag = not(self.PickingFlag)
	# 	self.UpdateRenderer()

	def setRegionColors(self,region_colors):
		assert len(region_colors) == self.nRegions
		self.region_colors = region_colors
		self.UpdateRenderer()

	def colorRelativeToRegion(self, regionId):
		self.regionId = regionId
		if not(self.communityMode):
			region_colors = [ self.colorTable.getColor(self.correlationTable.value(regionId, i)) for i in range(self.nRegions) ]
			region_colors[regionId] = self.selectedColor
			self.setRegionColors(region_colors)	

	# def MapGraphMetrics(self):
	# 	self.MapMetrics = not(self.MapMetrics)
	# 	self.addSpheres()
	# 	self.UpdateRenderer()

	def Community(self, Flag):
		self.communityMode = Flag

