# EARTHCODES
EARTHCODES Python package for processes-based geochemical modelling

WARNING:
This version is under active development and lacks full functionality, test cases, documentation and a full user guide.

EARTHCODES uses Array-based calculations (Numpy) to quickly calculate model geochemical compositions from mantle processes and compare these model results to real data, translating geochemical observations into physical mantle parameters.
EARTHCODES is a geochemical inversion software that keeps tracks of reservoir composition, but does not attribute size and location to reservoirs, instead modelling a fully independent mantle in each simulation. It is therefore not a box model.

Model compositions are stored as a ReservoirState dataclass, which stores elemental and isotopic compositions, as well as some physical parameters.

EARTHCODES is a modelling platform with the following built-in processes, that can be used to assemble a model architecture:
- edit: changes ReservoirState with a given composition (for example continental crust --> GLOSS)
- mix: mixes two ReservoirState to form one, with mixing proportions as a quantitative input. (for example Sediments + oceanic crust = recycled crust, or melt 1 + melt 2 = melt 3)
- melt: melts a source ReservoirState into a restite ReservoirState and a melt ReservoirState, with melting degree, Kds, and amount of rehomogenisation as quantitative inputs. (for example Peridotite = depleted peridotite + basaltic melt)
- uptake: adds trace elements from a fluid phase. Quantitative inputs are Max_budget and fraction f of Max_budget added. Do not include daughter elements in the budget, use mix instead with a radiogenic isotope composition for the fluid phase.
- leach: Dilutes the composition of ReservoirState as would be done through dehydration. Quantitative inputs are the mobility coefficients and the magnitude of leaching.

Minimal instructions for now:

Step 1:

Prior to creating a model on python, customise your model using the spreadsheet Model_architecture.xlsx. Assemble your model following the Beguelin_et_al_2025_G3_00xxx_model.xlsx example. A detailed guide will follow.
Model observables allow specifying which istope ratios are used in the model. Number of cells refers to the number of bins each dimension of the real data is discretised into. If number of cells = 30, the data will be discretised into 30 bins. Keep in mind that the number of cells in the multidimentional data grid is number_of_cells to the power of the number of observables. Try to keep this under 1 billion when running on a laptop, e.g. 30^6 = 720,000,000. Otherwise, the model will be extremely slow to run. The model should easily handle 10k-100k simulations per second. Try to adjust cells number and observable number if too slow.
Model output validity conditions allows rejecting simulations with trace element values artifcially too high. Models handling incompatible elements can easily lead to extreme trace element composition with low F fraction (low melting degree). This optional rejection criterion allows, for example, to reject final basalt compositions with Sr above 1000 ppm, etc.
Elements tracked specifies the list of elements tracked in the model, allowing to add elements that are not the mandatory parents and daughters elements (e.g. traking Ba, Ta, Nb, along with Sr, Rb, etc.).
Physical parameters to track are physical quantities that are modified through model processes, e.g. the cummulated degree of melt-depletion Fd (see Béguelin et al., 2025, G-Cubed 26(8)).
Processes build reservoirs from bottom to top with the most recent processes in the cells next to the label "a". Reservoir compositions are calculated from right to left and from bottom to top, with Reservoir_0 index a being the final model output (normally a present-day basalt).
- In the Times column, enter relative times labels. From younger to older: t0, t1, t2, t3, ..., t_init.
- In the Processes column, enter the name of the process that occurs at that time. Start building a new reservoir with edit, or mix (two reservoirs becoming a new one). The name of the process must be identical to the (lowercase) names of the built-in processes, and immediately followed by parentheses, such as edit(). If there is no argument in the parentheses, the input ReservoirState will be the output ReservoirState of the process in the cell right below, or a blank ReservoirState to be initialized with edit. To use the ReservoirState of a different cell, include a reservoir_index code as an argument such as 2_d for Reservoir_2 index d. Make sure that the ReservoirState passed as argument is either in a cell below or in a reservoir to the right, otherwise it will not exist in the model yet. For mix, enter the two ReservoirState to be mixed separated by a comma, such as mix(2_d, 3_a). Because melt has a two outputs (restite and melt), add either _melt or _restite to the reservoir_index code to specify the right ReservoirState to be used. For example, mix(1_a_melt, 2_a_melt) for a mixing of two melts.
- In the Comments columns, add a free comment to easily identitify what model step the model event corresponds to, for example: Solid-solid mixing between old model oceanic crust and GLOSS to form model ROC

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
Each subsequent sheet is a reservoir. Processes are listed in the same top to bottom order as in the architecture spreadsheet, this means time goes from bottom to top. Enter the min max values you want to explore the model with. If you want some variables to be linked across processes, such as scaling pyroxenite melting in the ROC reservoir with the peridotite melting in the peridotite reservoir, tick the global input box and select the same global input from the drop down menu in both processes. Any of the 20 "Global" variables can be used and become active in the model once selected. The model automatically detects variables and will treat a parameter as a constant if min = max. When linking two or more variables with a global input, if the global variable takes a random value of for example 0.2 in a given simulation, all the individual variables linked with it take the value that corresponds to 20% of their individual min-max ranges.
Save your model control workbook under a new name to avoid accidental overwriting. In python, enter the command:
  m.read_setup('The_new_control_workbook_name.xlsx')

Step 3:

Import model data. Your data file should be a .xlsx workbook with GEOROC-style headers. e.g. SR, RB, SM, ND for trace elements and SR87_SR86, ND143_ND144, PB206_PB204 for isotope ratios.
Use the following headers to inform the group hierarchy: Group_0, Group_1, Group_2, etc. For a sample, Group_0 might be OIB, Group_1 might be HAWAII, and Group_2 might be KILAUEA.
In Python, enter the command:
  m.read_data('Data.xlsx')

Step 4:

Run the model with the command:
  m.run(n_loops)
Where n_loops (an integer) is the number of Monte Carlo simulation batches to run. By default, each batch runs 50,000 simulations simultaneously. Therefore, enter m.run(20) to run 1 million simulations and m.run(20000) to run 1 billion simulations. Each individual simulation runs the customised model with random input values within the min-max intervals specified. The demo model (model 00GGG from Béguelin et al., 2025, G-Cubed 26(8)) with 6 observables (Sr, Nd, Hf, and 3 x Pb isotope ratios) runs at 5 loops per second on a 2021 MacBook Pro with no multithreading. 1 billion simulations can therefore be ran in ~ 1 hour on a similar machine.
While the model is running, the python console will display ASCII plots of binary isotope combinations showing a projection of the sample cells grid (n dimensions for n observables projected in 2 dimensions). Cells with no results are shown by dots in the ASCII plots. If a cell has been "hit" by a successful simulation, it turns into a square in the 2D projected location of that cell. If you cannot see the plot correctly, try to increase the size of your console window. Information displayed below the plots are:
- x-axis, y-axis: the names of the observables that are currently plotted
- n_loops: the loops counter (current / total loops)
- n_hits: how many simulations have been successful so far
- cells_with_any_results: how many cells have been "hit" by model results (cells hit / total number of cells)
- full_cells: number of cells with 100 results. By default, this is the maximum number of valid simulations the model will save per cell. To change it, enter
  m.max_results_per_cell = n
before running, with n being your desired results limit per cell.
By default, the model is running with a "naive" Monte Carlo engine, where the model tries random combination of values linearly distributed within the min-max intervals, regardless of which results are actually sucessful. Future updates of EARTHCODES may include a "latin squares" engine and possibly a results-aware strategy that devaluates combinations close to known unsuccessful modelling combinations as future guesses. Note that if most of your cells can receive a decent amount of results (e.g. > n_variables) with the "naive" method in a reasonable amount of time (less that one night), then the "naive" method should be priviledged over more clever approaches as it is the most accurate and unbiased modelling strategy. Also note that the cells_with_any_results counter failing to consistently increase during the a run should be interpreted as a negative finding, with the "unreachable" cells requiring an other conceptual model, different constants, and/or different min-max ranges (sometimes, narrowing a range can also increase the relative success rate of a model). And finally, remember that a negative finding is often more scientifically useful than a positive one.

Step 5:

Export your model results into a .xlsx workbook by entering the command:
  m.out()
This will output a .xlsx workbook called Model_results.xlsx with the values of all successful input variables for each sample of the original Data.xlsx sheet that received model results. For samples that received several successful model results, the reported values are the medoid of the input variables vector, which always corresponds to an acutal model result. Medoid calculations use the Mahalanobis distance. The Median Absolute Deviation (MAD) is also reported, which is effectively the model's "error", giving a sense of how sensitive input parameters are for a given sample (low error = very sensitive parameter, high error = not a sensitive input parameter). To include averages (means) of the results per group, enter the command
  m.out('Group_n')
where n is the desired group level (e.g. Group_1). This will create a second sheet in Model_results.xlsx with the results averaged for each group and the associated standard deviation of that average. Note that all samples of each groups are averaged without weighting. This means that for example, on the MORB-OIB global dataset, if the group level selected has a 'OIB' group for all OIB, Hawaii and Iceland will control the average due to their very high number of samples.
To add additional model outputs to the results sheet such as intermediate ReservoirState composition, intermediate variables and physical parameters, the .xlsx sheet Results_selection.xlsx can be used to customise the output of the model.out() method. The Results_selection.xlsx is automatically generated at the end of a model run and will be automatically read by model.out() (don't forget to save the workbook before reading it). This is however quite buggy at the moment with the drop-down menus in the workbook being prone to errors. Sorry.

Step 6 (bonus step):

Save your successful inputs into a .npz file for instant model re-running. After a model run, enter the command:
  m.save('name.npz')
Where name is a filename of your choice.
To re-run these inputs in a future modelling session enter the commands:
  m = model()
  m.build('The_exact_model_architecture_that_you_used.xlsx')
  m.read_setup('The_exact_filled_control_workbook_that_you_used_.xlsx')
  m.read_data('The_same_Data_file_that_you_used.xlsx')
  m.load('name.npz')

How to query model results in the python console:

Use the model.get() method.
After a model run, enter the command (use any name you want, "query" is an example):
  query = m.get(reservoir, event, idx)
where:
- reservoir: the numbered label of the reservoir that you want to query (e.g. 'Reservoir_0', 'Reservoir_1', etc.)
- event: the index letter of the model event that you want to query (e.g. 'a', 'b', 'c', etc.)
- idx (optional): the list of indices corresponding to the simulations that you want to extract. The indices list corresponding to each sample are listed in the dataframe m.data.results (column 'idx').
This will output a python dictionary with the model event's inputs, outputs and variables as keys. Inputs and outputs are nested dictionaries with the elements names, isotope ratio names and physical parameters names as keys.
