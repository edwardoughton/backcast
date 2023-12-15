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

data = data[complete.cases(data),]

data = select(data, year, radio, population, users, cells_to_build)

data = data %>%
  group_by(year, radio) %>%
  reframe(
    cells_to_build = sum(cells_to_build),
    users = round(sum(population),2),
    # population =  119565646, 
    # coverage_perc = round((sum(users)*4 / population) * 100,1),
  )

data = data %>%
  group_by(radio) %>%
  arrange(year) %>% 
  mutate(users = cumsum(users))

data$population = 130000000
data$coverage_perc = round((data$users / data$population) * 100,1)

data$radio = factor(data$radio,
     levels=c("gsm","umts","lte"),
     labels=c("2G GSM","3G UMTS","4G LTE")
)

data = select(data, year, radio, coverage_perc)


mini1<-data.frame(2016,"2G GSM", 98.3)
names(mini1)<-c('year', 'radio', 'coverage_perc')
data <- rbind(data, mini1)
mini1<-data.frame(2017,"2G GSM", 98.3)
names(mini1)<-c('year', 'radio', 'coverage_perc')
data <- rbind(data, mini1)
mini1<-data.frame(2018,"2G GSM", 98.3)
names(mini1)<-c('year', 'radio', 'coverage_perc')
data <- rbind(data, mini1)
mini1<-data.frame(2019,"2G GSM", 98.3)
names(mini1)<-c('year', 'radio', 'coverage_perc')
data <- rbind(data, mini1)
mini1<-data.frame(2020,"2G GSM", 98.3)
names(mini1)<-c('year', 'radio', 'coverage_perc')
data <- rbind(data, mini1)

totals <- data %>%
  group_by(radio, year) %>%
  summarize(coverage_perc = sum(coverage_perc))

# coverage = 
  ggplot(data, aes(x=year, y=coverage_perc, group=radio, fill=radio)) +
  geom_bar(stat="identity", position = position_dodge2(width = 0.9, preserve = "single")) +
  geom_text(aes(year, coverage_perc, label = paste(round(coverage_perc,0),"%"),  #y=0, 
                fill = NULL), show.legend = FALSE, 
            size = 1.5, data = totals, vjust=.5, hjust=-.2, 
            position = position_dodge(width = .9), angle = 90) +
  theme(legend.position = 'bottom',
      axis.text.x = element_text(angle=0, hjust=.5)) +
  scale_fill_brewer(palette="Paired")+
  labs(colour=NULL,
       title = "Evaluation of Geospatial Backcast of Mobile Deployment",
       subtitle = "Reported for Mexico between 2000-2020.", 
       x = "Year", y = "Population Coverage (%)",  fill=NULL) + 
  scale_y_continuous(expand = c(0, 0), limits=c(0, 110),
                     breaks = seq(0, 150, by = 20))

path = file.path(folder, 'figures', 'coverage_pop.png')
ggsave(path, units="in", width=6, height=4, dpi=300)
