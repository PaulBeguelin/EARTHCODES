# EARTHCODES
EARTHCODES Python package for processes-based geochemical modelling

WARNING:
This version is under active development and lacks full functionality, test cases, documentation and a full user guide.

EARTHCODES uses Array-based calculations (Numpy) to quickly calculate model geochemical composition from mantle processes and compare these model results to real data, translating geochemical observations into physical mantle parameters.
EARTHCODES is a geochemical inversion software that keeps tracks of reservoir composition, but does not attribute size and location to reservoirs, instead modelling a fully independent mantle in each simulation. It is therefore not a box model.

Model compositions are stored as a ReservoirState dataclass, which stores elemental and isotopic compositions, as well as some physical parameters.

EARTHCODES is a modelling platform with the following built-in processes, that can be used to assemble a model architecture:
- edit: changes ReservoirState with a given composition (for example continental crust --> GLOSS)
- mix: mixes two ReservoirState to form one, with mixing proportions as a quantitative input. (for example Sediments + oceanic crust = recycled crust, or melt 1 + melt 2 = melt 3)
- melt: melts a source ReservoirState into a restite ReservoirState and a melt ReservoirState, with melting degree, Kds, and amount of rehomogenisation as quantitative inputs. (for example Peridotite = depleted peridotite + basaltic melt)
- uptake: adds trace elements from a fluid phase. Quantitative inputs are Max_budget and fraction f of Max_budget added. Do not include daughter elements in the budget, use mix instead with a radiogenic isotope composition for the fluid phase.
- leach: Dilutes the composition of ReservoirState as would be done through dehydration. Quantitative inputs are the mobility coefficient and the magnitude of leaching.

Minimal instructions for now:

Step 1:

Prior to creating a model on python, customise your model using the spreadsheet Model_architecture.xlsx. Assemble your model following the Beguelin_et_al_2025_G3_00xxx_model.xlsx example. A detailed guide will follow.
Model observables allow specifying which istope ratios are used in the model. Number of cells refers to the number of bins each dimension of the real data is discretised into. If number of cells = 30, the data will be discretised into 30 bins. Keep in mind that the number of cells in the multidimentional data grid is number_of_cells to the power of the number of observables. Try to keep this under 1 billion when running on a laptop, e.g. 30^6 = 720,000,000. Otherwise, the model will be extremely slow to run. The model should easily handle ~0.5 million simulations per second. Try to adjust cells number and observable number if too slow.
Model output validity conditions allows rejecting simulations with trace element values artifcially too high. Models handling incompatible elements can easily lead to extreme trace element composition with low F fraction (low melting degree). This optional rejection close allows, for example, to reject final basalt compositions with Sr above 1000 ppm, etc.
Elements tracked specifies the list of elements tracked in the model, allowing to add elements that are not the mandatory parents and daughters elements (e.g. traking Ba, Ta, Nb, along with Sr, Rb, etc.).
Physical parameters to track are physical quantities that are modified through model processes, e.g. the cummulated degree of melt-depletion Fd (see Béguelin et al., 2025, G-Cubed 26(8)).
Processes build reservoirs from bottom to top with the most recent processes in the cells next to the label "a". Reservoir compositions are calculated from right to left and from bottom to top, with Reservoir_0 index a being the final model output (normally a present-day basalt).
- In the Times column, enter relative times labels. From older to youger: t_init, ..., t5, t4, t3, t2, t1, t0
- In the Processes column, enter the name of the process that occurs at that time. Start building a new reservoir with edit, or mix (two reservoirs becoming a new one). The name of the process must be identical to the (lowercase) names of the built-in processes, and immediately followed by parentheses, such as edit(). If there is no argument in the parentheses, the input ReservoirState will be the output ReservoirState of the process in the cell right below, or a blank ReservoirState to be initialized with edit. To use the ReservoirState of a different cell, include a reservoir_index code as an argument such as 2_d for Reservoir_2 index d. Make sure that the ReservoirState passed as argument is either in a cell below or in a reservoir to the right, otherwise it will not exist in the model yet. For mix, enter the two ReservoirState to be mixed separated by a comma, such as mix(2_d, 3_a). Because melt has a two outputs (restite and melt), add either _melt or _restite to the reservoir_index code to specify the right ReservoirState to be used. For example, mix(1_a_melt, 2_a_melt) for a mixing of two melts.
- In the Commnents columns, add a free comment to easily identitify what model step the model event corresponds to, for example: Solid-solid mixing between old model oceanic crust and GLOSS to form model ROC

Step 2:

in model.py, run:
  m = model()
This creates a blank model.
Read your Model_architecture.xlsx file with the command:
  m.build(Model_architecture.xlsx)
(change Model_architecture.xlsx with the actual name of your model architecture file, e.g. Beguelin_et_al_2025_G3_00xxx_model.xlsx for the demo)
This will output a model control workbook for you to customise the individual processes of your model.
The output file will have the same name as your model architecture file, but with _control_workbook.xlsx at the end.
In this control workbook file, set the min max ranges in Time ranges (note that units are in Ga, so enter 1.0 for 1 billion years BP).
Each subsequent sheet is a reservoir. Processes are listed in the same top to bottom as in the architecture spreadsheet, this means time goes from bottom to top. Enter the min max values you want to explore the model with. If you want some variables to be linked across processes, such as scaling pyroxenite melting in the ROC reservoir with the peridotite melting in the peridotite reservoir, tick the global input box and select the same global input from the drop down menu in both processes. Any of the 20 "Global" variables can be used and become active in the model once selected. The model automatically detects variables and will treat a parameter as a constant if min = max.
Save your model control workbook under a new name to avoid accidental overwriting. In python, enter the command:
  m.read_setup('The_new_control_workbook_name.xlsx')

Step 3:

Import model data. Your data file should be a .xlsx workbook with GEOROC-style headers. e.g. SR, RB, SM, ND for trace elements and SR87_SR86, ND143_ND144, PB206_PB204 for isotope ratios.
Use the following headers to inform the group hierarchy: Group_0, Group_1, Group_2, etc. For a sample, Group_0 might be OIB, Group_1 might be HAWAII, and Group_2 might be KILAUEA.
In Python, enter the command:
  m.read_data('Data.xlsx')

