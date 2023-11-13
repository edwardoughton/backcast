###VISUALISE MODEL OUTPUTS###
# install.packages("tidyverse")
library(tidyverse)
# install.packages("ggpubr")
library(ggpubr)

iso3 = 'MEX'

####
folder = dirname(rstudioapi::getSourceEditorContext()$path)
path_in = file.path(folder, '..', 'results',iso3,'results.csv')
data = read.csv(path_in)

data = data %>%
  group_by(year, radio) %>%
  reframe(
    cells_to_build = sum(cells_to_build),
    cost = sum(cost),
    population_served = sum(population_served)
  )

test = data %>%
  select(year, radio, cells_to_build) %>%
  group_by(year, radio) %>%
  reframe(
    cells_to_build = cumsum(cells_to_build) #/ sum(cells_to_build)
  )

test2 = test %>%
  group_by(year, radio) %>%
  reframe(
    cells_to_build = cumsum(cells_to_build) / sum(cells_to_build)
  )

pdf = data %>% 
  select(year, radio, cells_to_build) %>%
  group_by(year, radio) %>% 
  arrange(year, radio) %>% 
  mutate(cells_to_build = cumsum(cells_to_build) * sum(cells_to_build))

