from op import Registry, async_
import rate_limiter
from backends.brickowl import BrickOwl
from models import Part
import os
import urllib.request 
from urllib.error import HTTPError



@Registry.register
class lookup_part_bo_id:
    params = [
        'part_id'
    ]
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        saved_op = self.saved_op

        part_id = saved_op.params['part_id']
        part = self.session.query(Part) \
            .filter_by(id=part_id) \
            .first()

        if part.id_bo != None:
            return

        brickowl = BrickOwl.from_user(self.user)
        boids = brickowl.catalog_id_lookup(part_id, 'Part')['boids']
        if len(boids) == 0:
            print(f"WARNING: Part \"{part.name}\" ({part.id}) couldn't be matched with BO.")
            return
        
        boid = boids[0].split('-')[0]  # Trims color (after - on BOIDs)
        part.id_bo = boid


@Registry.register
class retrieve_bl_part_image:
    params = [
        'color_id',
        'part_id'
    ]
    rate_limiter = rate_limiter.bricklink

    def execute(self):


