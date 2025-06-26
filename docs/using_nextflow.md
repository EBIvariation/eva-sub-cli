# Using Nextflow for Parallelization  

Nextflow is a common workflow management system that helps orchestrate tasks and interface with the execution engine (like HPC or cloud). When running natively (i.e. not using Docker), eva-sub-cli will use Nextflow to run all the validation steps. In this section we'll see how it can be parameterised to work with your compute infrastructure.

When no options are provided, Nextflow will run as many tasks as there are available CPUs on the machine executing it. To modify how many tasks can start and how Nextflow will process each one, you can provide a Nextflow configuration file in several ways.

From the command line you can use `--nextflow_config <path>` to specify the Nextflow config file you want to apply. The configuration can also be picked up from other places directly by Nextflow. Please refer to [the Nextflow documentation](https://www.nextflow.io/docs/latest/config.html) for more details.

## Basic Nextflow configuration

There are many options to configure Nextflow so we will not provide them all. Please refer to [the documentation](https://www.nextflow.io/docs/latest/reference/config.html) for advanced features.
Below is a very basic Nextflow configuration file that will request 2 cpus for each process, essentially limiting the number of process to half the number of available CPUs 
```
process {
    executor="local"
    cpus=2
}
```
In this configuration, all the process will be running on the same machine where eva-sub-cli was started as described in the schema below.
```
(Local machine)
eva-sub-cli
  |_ nextflow
      |_ task1
      |_ task2
```

## Basic Nextflow configuration for HPC use

If you have access to High Performance Compute (HPC) environment, Nextflow supports the main resource managers such as [SLURM](https://www.nextflow.io/docs/latest/executor.html#slurm), [SGE](https://www.nextflow.io/docs/latest/executor.html#sge), [LSF](https://www.nextflow.io/docs/latest/executor.html#lsf) and others.
In the configuration below, we're assuming that you are using SLURM. It would work similarly with other resource managers.
```
process {
    executor="slurm"
    queue="my_production_queue"
}
```

In this configuration, the subtasks will be performed in other machines as specified by your SLURM resource manager as described in the schema below.
```
(Local machine)
eva-sub-cli
  |_ nextflow
(Other compute node)
task1
(Other compute node)
task2
```
