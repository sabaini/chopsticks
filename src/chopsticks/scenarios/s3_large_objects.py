import os
from locust import task, between
from chopsticks.workloads.s3.s3_workload import S3Workload


class S3LargeObjectTest(S3Workload):
    """
    S3 Large Object Stress Test
    
    Tests upload and download of large objects to simulate
    real-world large file workloads.
    
    Environment Variables:
        LARGE_OBJECT_SIZE: Size of objects in MB (default: 100)
        UPLOAD_WEIGHT: Weight for upload task (default: 3)
        DOWNLOAD_WEIGHT: Weight for download task (default: 2)
    """
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize test parameters"""
        self.object_size_mb = int(os.environ.get('LARGE_OBJECT_SIZE', '100'))
        self.object_size_bytes = self.object_size_mb * 1024 * 1024
        self.uploaded_keys = []
    
    @task(3)
    def upload_large_object(self):
        """Upload a large object"""
        key = self.generate_key(prefix=f"large-objects/{self.object_size_mb}mb")
        data = self.generate_data(self.object_size_bytes)
        
        success = self.client.upload(key, data)
        
        if success:
            self.uploaded_keys.append(key)
            # Keep only last 10 keys to avoid memory issues
            if len(self.uploaded_keys) > 10:
                self.uploaded_keys.pop(0)
    
    @task(2)
    def download_large_object(self):
        """Download a previously uploaded large object"""
        if not self.uploaded_keys:
            return
        
        # Download a random uploaded object
        import random
        key = random.choice(self.uploaded_keys)
        
        data = self.client.download(key)
        
        if data:
            # Verify size
            if len(data) != self.object_size_bytes:
                raise Exception(
                    f"Downloaded object size mismatch: expected {self.object_size_bytes}, "
                    f"got {len(data)}"
                )
    
    @task(1)
    def delete_large_object(self):
        """Delete a large object"""
        if not self.uploaded_keys:
            return
        
        key = self.uploaded_keys.pop(0)
        self.client.delete(key)
