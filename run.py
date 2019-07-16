#!/usr/bin/env python3

import os
import logging
import shutil
import subprocess
import flywheel
import nibabel as nib


log = logging.getLogger('[flywheel/fsl-siena]')


def validate_nifti(nifti_name, nifti_input_path):
    try:
        # Try loading with nibabel
        nib.load(nifti_input_path)
        log.info('Valid NIfTI file provided {}: {}'.format(nifti_name, nifti_input_path))

    except nib.loadsave.ImageFileError:
        log.error('Invalid NIfTI file provided for input {}: {}'.format(nifti_name, nifti_input_path))
        log.error('Siena/SienaX will not run. Exiting...')
        os.sys.exit(1)

    # Fix spaces in file name
    nifti_folder = os.path.dirname(nifti_input_path)
    nifti_basename = os.path.basename(nifti_input_path).replace(' ', '_')
    nifti_path = os.path.join(nifti_folder, nifti_basename)
    # If spaces were fixed, copy file and log info
    if nifti_path != nifti_input_path:
        shutil.copyfile(nifti_input_path, nifti_path)
        log.info('{} filename contains spaces: {}'.format(nifti_name, nifti_input_path))
        log.info('{} moved to: {}'.format(nifti_name, nifti_path))

    return nifti_path


def create_options_list(config, siena_or_sienax):
    # Initialize options list
    options_list = list()

    # Append common booleans
    if config.get('DEBUG'):
        options_list.append('-d')
    if config.get('SEG'):
        options_list.append('-2')
    if config.get('T2'):
        options_list.append('-t2')

    # Append common strings
    bet_options = config.get('BET')
    if bet_options != '':
        options_list.append('-B')
        # BET options must be wrapped in double quotes
        if not bet_options.startswith('"'):
            bet_options = '"{}"'.format(bet_options)
        options_list.append(bet_options)
    bottom_boundary = config.get('BOTTOM')
    if bottom_boundary != '':
        options_list.append('-b')
        options_list.append(bottom_boundary)
    top_boundary = config.get('TOP')
    if top_boundary != '':
        options_list.append('-t')
        options_list.append(top_boundary)

    # SIENA-specific options
    if siena_or_sienax == 'siena':
        # Add SIENA-specific boolean flags
        if config.get('SS_BET'):
            options_list.append('-m')
        if config.get('VENT'):
            options_list.append('-V')
        # Add SIENA-specific string options
        siena_diff_options = config.get('S_DIFF')
        if siena_diff_options != '':
            options_list.append('-S')
            if not siena_diff_options.startswith('"'):
                siena_diff_options = '"{}"'.format(siena_diff_options)
            options_list.append(siena_diff_options)

    # SIENAX-specific options
    elif siena_or_sienax == 'sienax':
        # Add SIENAX-specific boolean flags
        if config.get('REGIONAL'):
            options_list.append('-r')

        # Add SIENAX-specific string options
        fast_options_sienax = config.get('S_FAST')
        if fast_options_sienax != '':
            options_list.append('-S')
            # FAST options must be wrapped in double quotes
            if not fast_options_sienax.startswith('"'):
                fast_options_sienax = '"{}"'.format(fast_options_sienax)
            options_list.append(fast_options_sienax)
    # Handle function misuse
    else:
        log.error('Invalid siena_or_sienax string provided: {}'.format(siena_or_sienax))
        log.error('Algorithm will not run. Exiting...')
        os.sys.exit(1)
    # Return options list
    return options_list


if __name__ == '__main__':
    with flywheel.GearContext() as gear_context:

        # Initialize gear logging
        gear_context.init_logging()
        log.info('Starting FSL: SIENA/SIENAX gear...')

        # Get output filepath
        output_directory = gear_context.output_dir

        # Get config options
        config = gear_context.config
        log.info('Config type {}'.format(type(config)))

        # Initialize command_list
        command_list = list()

        # Determine if SIENA or SIENAX
        if gear_context.get_input('NIFTI_1') and gear_context.get_input('NIFTI_2'):
            log.info('Getting FSL SIENA Configuration...')
            # Add siena command to command list
            command_list.append('siena')
            # Get inputs from manifest
            nifti_1 = gear_context.get_input('NIFTI_1')
            nifti_2 = gear_context.get_input('NIFTI_2')
            ventricle_mask = gear_context.get_input('ventricle_mask')
            # Validate inputs and append to command
            nifti_1_path = validate_nifti('nifti_1', nifti_1['location']['path'])
            command_list.append(nifti_1_path)
            nifti_2_path = validate_nifti('nifti_2', nifti_2['location']['path'])
            command_list.append(nifti_2_path)

            # Get options from config
            command_options = create_options_list(config, 'siena')
            # Add optional ventricle mask to options
            if ventricle_mask:
                ventricle_mask_path = validate_nifti('ventricle_mask', ventricle_mask['location']['path'])
                command_options.append('-v')
                command_options.append(ventricle_mask_path)
            # Add options to command list
            command_list = command_list + command_options

        elif gear_context.get_input('NIFTI'):
            log.info('Getting FSL SIENAX Configuration...')
            # Add sienax command to command list
            command_list.append('sienax')
            # Get inputs from manifest
            nifti = gear_context.get_input('NIFTI')
            # Validate inputs
            nifti_path = validate_nifti('nifti', nifti['location']['path'])
            command_list.append(nifti_path)
            lesion_mask = gear_context.get_input('lesion_mask')
            # Get options from config
            command_options = create_options_list(config, 'sienax')
            if lesion_mask:
                lesion_mask_path = validate_nifti('lesion_mask', lesion_mask['location']['path'])
            # Add options to command list
            command_list = command_list + command_options

        else:
            log.error('Invalid manifest.json file provided for FSL SIENA/SIENAX')
            log.error('Algorithm will not run. Exiting...')
            os.sys.exit(1)

        # Add output directory to command list
        command_list.append('-o')
        command_list.append('output_directory')

        # Echo command before running
        echo_command = list()
        echo_command.append('echo')
        echo_command = echo_command + command_list

        log.info('Running FSL {}...'.format(command_list[0].upper()))
        subprocess.run(echo_command)
        subprocess.run(command_list)